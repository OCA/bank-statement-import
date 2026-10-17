# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
from unittest.mock import MagicMock, patch

import requests
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

from .test_account_statement_import_online_ponto import FOUR_TRANSACTIONS


class TestPontoInterface(common.TransactionCase):
    post_install = True

    def test_http_rejects_untrusted_transaction_urls(self):
        interface = self.env["ponto.interface"]
        for url in (
            "http://127.0.0.1",
            "http://2130706433",
            "http://0x7f000001",
            "http://[::1]",
            "http://169.254.169.254/latest",
            "http://api.myponto.com",
            "//api.myponto.com",
            "https://api.myponto.com.evil.invalid",
            "https://api.myponto.com@evil.invalid",
            "https://evil.invalid@api.myponto.com",
            "https://api.myponto.com:444",
            "https://api.myponto.com:invalid",
            "https://[broken",
            "https://api.myponto.com#fragment",
            "https://api.myponto.com\n.evil.invalid",
            "file:///etc",
            "gopher://localhost",
        ):
            with (
                self.subTest(url=url),
                patch.object(type(interface), "_get_request_headers") as headers,
                patch("requests.get") as request,
                self.assertRaisesRegex(UserError, "official Ponto HTTPS"),
            ):
                try:
                    interface._get_request({}, url, {})
                finally:
                    headers.assert_not_called()
                    request.assert_not_called()

    def test_http_rejects_redirects_on_every_request_path(self):
        interface = self.env["ponto.interface"]
        for status in (301, 302, 303, 307, 308):
            for target in ("http://127.0.0.1/private", "https://untrusted.invalid/"):
                for path in ("login", "accounts", "transactions"):
                    response = requests.Response()
                    response.status_code = status
                    response.headers["Location"] = target
                    response._content = b"{}"
                    response.request = requests.Request(
                        "POST" if path == "login" else "GET", "https://api.myponto.com"
                    ).prepare()
                    response.url = response.request.url
                    with (
                        self.subTest(status=status, target=target, path=path),
                        patch.object(
                            type(interface),
                            "_get_request_headers",
                            return_value={"Authorization": "Bearer dummy-token"},
                        ),
                        patch("requests.sessions.get_environ_proxies", return_value={}),
                        patch(
                            "requests.adapters.HTTPAdapter.send",
                            side_effect=[response, AssertionError("Redirect followed")],
                        ) as transport,
                        self.assertRaisesRegex(UserError, "redirects are not allowed"),
                    ):
                        try:
                            if path == "login":
                                interface._login("dummy-user", "dummy-secret")
                            elif path == "accounts":
                                interface._set_access_account({}, "DUMMY-ACCOUNT")
                            else:
                                interface._get_request(
                                    {},
                                    "https://api.myponto.com/accounts/dummy/transactions",
                                    {},
                                )
                        finally:
                            transport.assert_called_once()

    def test_http_preserves_token_refresh_pagination_and_safe_url_forms(self):
        interface = self.env["ponto.interface"]
        for authority in ("api.myponto.com", "API.MYPONTO.COM:443"):
            access = self._get_access_dict()
            access["token_expiration"] = fields.Datetime.now() - relativedelta(
                seconds=1
            )
            token_response = requests.Response()
            token_response.status_code = 200
            token_response._content = (
                b'{"access_token":"refreshed-dummy","expires_in":1800}'
            )
            transaction_response = requests.Response()
            transaction_response.status_code = 200
            transaction_response._content = b'{"data":[]}'
            with (
                self.subTest(authority=authority),
                patch("requests.sessions.get_environ_proxies", return_value={}),
                patch(
                    "requests.adapters.HTTPAdapter.send",
                    side_effect=[token_response, transaction_response],
                ) as transport,
            ):
                result = interface._get_request(
                    access,
                    f"https://{authority}/accounts/dummy/transactions",
                    {"after": "previous-id", "limit": 100},
                )
            self.assertEqual(result, {"data": []})
            self.assertEqual(access["access_token"], "refreshed-dummy")
            self.assertEqual(transport.call_count, 2)
            login, get = (call.args[0] for call in transport.call_args_list)
            self.assertEqual(login.method, "POST")
            self.assertEqual(
                login.url,
                "https://api.myponto.com/oauth2/token?grant_type=client_credentials",
            )
            self.assertTrue(login.headers["Authorization"].startswith("Basic "))
            self.assertEqual(get.headers["Authorization"], "Bearer refreshed-dummy")
            self.assertTrue(
                get.url.startswith(
                    "https://api.myponto.com/accounts/dummy/transactions?"
                )
            )
            self.assertIn("after=previous-id", get.url)
            self.assertEqual(transport.call_args.kwargs["timeout"], (60, 300))

    @patch("requests.post")
    def test_login(self, requests_post):
        """Check Ponto API login."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "access_token": "live_the_token",
                "expires_in": 1799,
                "scope": "ai",
                "token_type": "bearer",
            }
        )
        requests_post.return_value = mock_response
        interface_model = self.env["ponto.interface"]
        access_data = interface_model._login("uncle_john", "secret")
        self.assertEqual(access_data["access_token"], "live_the_token")
        self.assertIn("token_expiration", access_data)

    @patch("requests.get")
    def test_set_access_account(self, requests_get):
        """Test getting account data for Ponto access."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "data": [
                    {
                        "id": "wrong_id",
                        "attributes": {
                            "reference": "NL66ABNA123456789",
                        },
                    },
                    {
                        "id": "2ad3df83-be01-47cf-a6be-cf0de5cb4c99",
                        "attributes": {
                            "reference": "NL66RABO123456789",
                        },
                    },
                ],
            }
        )
        requests_get.return_value = mock_response
        # Start of actual test.
        access_data = self._get_access_dict(include_account=False)
        interface_model = self.env["ponto.interface"]
        interface_model._set_access_account(access_data, "NL66RABO123456789")
        self.assertIn("ponto_account", access_data)
        self.assertEqual(
            access_data["ponto_account"], "2ad3df83-be01-47cf-a6be-cf0de5cb4c99"
        )

    @patch("requests.get")
    def test_get_transactions(self, requests_get):
        """Test getting transactions from Ponto."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Key "data" will contain a list of transactions.
        mock_response.text = json.dumps({"data": FOUR_TRANSACTIONS})
        requests_get.return_value = mock_response
        # Start of actual test.
        access_data = self._get_access_dict()
        interface_model = self.env["ponto.interface"]
        transactions = interface_model._get_transactions(access_data, False)
        self.assertEqual(len(transactions), 4)
        self.assertEqual(transactions[3]["id"], "b21a6c65-1c52-4ba6-8cbc-127d2b2d85ff")
        self.assertEqual(
            transactions[3]["attributes"]["counterpartReference"], "BE10325927501996"
        )

    def _get_access_dict(self, include_account=True):
        """Get access dict that caches login/account information."""
        token_expiration = fields.Datetime.now() + relativedelta(seconds=1800)
        access_data = {
            "username": "uncle_john",
            "password": "secret",
            "access_token": "live_the_token",
            "token_expiration": token_expiration,
        }
        if include_account:
            access_data["ponto_account"] = "2ad3df83-be01-47cf-a6be-cf0de5cb4c99"
        return access_data
