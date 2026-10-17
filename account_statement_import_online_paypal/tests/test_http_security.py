# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from email.message import Message
from io import BytesIO
from unittest.mock import patch
from urllib.response import addinfourl

from odoo.exceptions import UserError
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestPayPalHttpSecurity(BaseCommon):
    def _response(self, status=200, location=None):
        headers = Message()
        if location:
            headers["Location"] = location
        response = addinfourl(
            BytesIO(b"{}"), headers, "https://api.paypal.com/v1/test", status
        )
        response.msg = "test"
        return response

    def test_official_endpoints_and_authentication(self):
        provider = self.env["online.bank.statement.provider"]
        for host in (
            "api.paypal.com",
            "api-m.paypal.com",
            "api.sandbox.paypal.com",
            "api-m.sandbox.paypal.com",
        ):
            for authority in (host, host.upper() + ":443"):
                for auth, expected, data in (
                    ("dummy-token", "Bearer dummy-token", None),
                    (
                        ("dummy", "dummy"),
                        "Basic ZHVtbXk6ZHVtbXk=",
                        b"grant_type=client_credentials",
                    ),
                ):
                    with (
                        self.subTest(host=authority, auth=expected),
                        patch("urllib.request.getproxies", return_value={}),
                        patch(
                            "urllib.request.HTTPSHandler.https_open",
                            return_value=self._response(),
                        ) as transport,
                    ):
                        result = provider._paypal_retrieve(
                            f"https://{authority}/v1/test?page=2", auth, data=data
                        )
                        self.assertEqual(result, {})
                        transport.assert_called_once()
                        request = transport.call_args.args[0]
                        self.assertEqual(
                            request.full_url, f"https://{host}/v1/test?page=2"
                        )
                        self.assertEqual(request.get_header("Authorization"), expected)
                        self.assertEqual(request.data, data)

    def test_accountant_cannot_redirect_credentials(self):
        accountant = new_test_user(
            self.env,
            login="paypal_endpoint_accountant",
            groups="account.group_account_user",
        )
        self.assertFalse(accountant.has_group("base.group_system"))
        journal = self.env["account.journal"].create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PPSEC",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )
        provider = journal.online_bank_statement_provider_id.with_user(accountant)
        provider.username = "dummy"
        provider.password = "dummy"
        for base in (
            "http://127.0.0.1",
            "http://2130706433",
            "http://0x7f000001",
            "http://[::1]",
            "http://169.254.169.254/latest",
            "http://api.paypal.com",
            "https://api.paypal.com:444",
            "https://api.paypal.com:invalid",
            "https://api.paypal.com:65536",
            "https://[broken",
            "//api.paypal.com",
            "https://api.paypal.com.evil.invalid",
            "https://api.paypal.com@evil.invalid",
            "https://evil.invalid@api.paypal.com",
            "https://api.paypal.com\\@localhost",
            "https://api.paypal.com#fragment",
            "https://api.paypal.com\n.evil.invalid",
            "file:///etc",
            "gopher://localhost",
            "https://api.wise.com",
        ):
            with (
                self.subTest(base=base),
                patch("urllib.request.Request") as request,
                patch("urllib.request.build_opener") as opener,
            ):
                provider.api_base = base
                with self.assertRaisesRegex(UserError, "official PayPal HTTPS"):
                    provider._paypal_get_token()
                request.assert_not_called()
                opener.assert_not_called()

    def test_redirects_never_receive_basic_or_bearer_authentication(self):
        provider = self.env["online.bank.statement.provider"]
        for status in (301, 302, 303, 307, 308):
            for target in ("http://127.0.0.1/private", "https://untrusted.invalid/"):
                for auth, data in (
                    ("dummy-token", None),
                    (("dummy", "dummy"), b"grant_type=client_credentials"),
                ):
                    with (
                        self.subTest(status=status, target=target, post=bool(data)),
                        patch("urllib.request.getproxies", return_value={}),
                        patch(
                            "urllib.request.HTTPSHandler.https_open",
                            side_effect=[
                                self._response(status, target),
                                AssertionError("Redirect followed"),
                            ],
                        ) as https,
                        patch("urllib.request.HTTPHandler.http_open") as http,
                        self.assertRaisesRegex(UserError, "redirects are not allowed"),
                    ):
                        try:
                            provider._paypal_retrieve(
                                "https://api.paypal.com/v1/test", auth, data=data
                            )
                        finally:
                            https.assert_called_once()
                            http.assert_not_called()
