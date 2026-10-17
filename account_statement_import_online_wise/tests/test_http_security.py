# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from email.message import Message
from io import BytesIO
from unittest.mock import Mock, patch
from urllib.error import HTTPError
from urllib.response import addinfourl

from odoo.exceptions import UserError
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestWiseHttpSecurity(BaseCommon):
    def _response(self, status=200, location=None):
        headers = Message()
        if location:
            headers["Location"] = location
        response = addinfourl(
            BytesIO(b"[]"), headers, "https://api.wise.com/v1/profiles", status
        )
        response.msg = "test"
        return response

    def _sca_challenge(self):
        headers = Message()
        headers["X-2FA-Approval-Result"] = "REJECTED"
        headers["X-2FA-Approval"] = "dummy-challenge"
        return HTTPError(
            "https://api.wise.com/v1/profiles", 403, "Forbidden", headers, BytesIO()
        )

    def test_official_endpoints_and_signed_authentication(self):
        provider = self.env["online.bank.statement.provider"]
        for host in (
            "api.wise.com",
            "api.transferwise.com",
            "api.wise-sandbox.com",
            "api.sandbox.transferwise.tech",
            "api.sandbox.wise.tech",
        ):
            for authority in (host, host.upper() + ":443"):
                with (
                    self.subTest(host=authority),
                    patch("urllib.request.getproxies", return_value={}),
                    patch(
                        "urllib.request.HTTPSHandler.https_open",
                        return_value=self._response(),
                    ) as transport,
                ):
                    with provider._wise_urlopen(
                        f"https://{authority}/v1/profiles?page=2",
                        "dummy-token",
                        "dummy-ott",
                        "dummy-signature",
                    ) as response:
                        self.assertEqual(response.read(), b"[]")
                    transport.assert_called_once()
                    request = transport.call_args.args[0]
                    self.assertEqual(
                        request.full_url, f"https://{host}/v1/profiles?page=2"
                    )
                    self.assertEqual(
                        request.get_header("Authorization"), "Bearer dummy-token"
                    )
                    self.assertEqual(request.get_header("X-2fa-approval"), "dummy-ott")
                    self.assertEqual(
                        request.get_header("X-signature"), "dummy-signature"
                    )

    def test_accountant_endpoint_and_profile_context_are_rejected(self):
        accountant = new_test_user(
            self.env,
            login="wise_endpoint_accountant",
            groups="account.group_account_user",
        )
        self.assertFalse(accountant.has_group("base.group_system"))
        journal = self.env["account.journal"].create(
            {
                "name": "Wise",
                "type": "bank",
                "code": "WISEC",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "transferwise",
            }
        )
        provider = journal.online_bank_statement_provider_id.with_user(accountant)
        provider.password = "dummy-token"
        for base in (
            "http://127.0.0.1",
            "http://2130706433",
            "http://0x7f000001",
            "http://[::1]",
            "http://169.254.169.254/latest",
            "http://api.wise.com",
            "https://api.wise.com:444",
            "https://api.wise.com:invalid",
            "https://api.wise.com:65536",
            "https://[broken",
            "//api.wise.com",
            "https://api.wise.com.evil.invalid",
            "https://api.wise.com@evil.invalid",
            "https://evil.invalid@api.wise.com",
            "https://api.wise.com\\@localhost",
            "https://api.wise.com#fragment",
            "https://api.wise.com\n.evil.invalid",
            "file:///etc",
            "gopher://localhost",
            "https://api.paypal.com",
        ):
            with (
                self.subTest(base=base),
                patch("urllib.request.Request") as request,
                patch("urllib.request.build_opener") as opener,
            ):
                provider.api_base = base
                with self.assertRaisesRegex(UserError, "official Wise HTTPS"):
                    provider._obtain_statement_data(
                        datetime(2026, 1, 1),
                        datetime(2026, 1, 2),
                    )
                with self.assertLogs(
                    "odoo.addons.account_statement_import_online_wise.models.online_bank_statement_provider_wise",
                    level="WARNING",
                ):
                    self.assertEqual(
                        provider.with_context(
                            api_base=base, api_key="dummy-token"
                        ).values_wise_profile(),
                        [],
                    )
                request.assert_not_called()
                opener.assert_not_called()

    def test_sca_retry_preserves_authentication(self):
        provider = self.env["online.bank.statement.provider"]
        signing_key = Mock()
        signing_key.sign.return_value = b"dummy-signature"
        with (
            patch("urllib.request.getproxies", return_value={}),
            patch(
                "urllib.request.HTTPSHandler.https_open",
                side_effect=[self._sca_challenge(), self._response()],
            ) as transport,
        ):
            self.assertEqual(
                provider._wise_retrieve(
                    "https://api.wise.com/v1/profiles", "dummy-token", signing_key
                ),
                [],
            )
        signing_key.sign.assert_called_once()
        self.assertEqual(signing_key.sign.call_args.args[0], b"dummy-challenge")
        self.assertEqual(transport.call_count, 2)
        request = transport.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer dummy-token")
        self.assertEqual(request.get_header("X-2fa-approval"), "dummy-challenge")
        self.assertEqual(request.get_header("X-signature"), "ZHVtbXktc2lnbmF0dXJl")

    def test_initial_and_signed_retry_redirects_are_rejected(self):
        provider = self.env["online.bank.statement.provider"]
        for status in (301, 302, 303, 307, 308):
            for target in ("http://127.0.0.1/private", "https://untrusted.invalid/"):
                for challenge in (False, True):
                    responses = [
                        self._response(status, target),
                        AssertionError("Redirect followed"),
                    ]
                    if challenge:
                        responses.insert(0, self._sca_challenge())
                    signing_key = Mock()
                    signing_key.sign.return_value = b"dummy-signature"
                    with (
                        self.subTest(status=status, target=target, challenge=challenge),
                        patch("urllib.request.getproxies", return_value={}),
                        patch(
                            "urllib.request.HTTPSHandler.https_open",
                            side_effect=responses,
                        ) as https,
                        patch("urllib.request.HTTPHandler.http_open") as http,
                        self.assertRaisesRegex(UserError, "redirects are not allowed"),
                    ):
                        try:
                            provider._wise_retrieve(
                                "https://api.wise.com/v1/profiles",
                                "dummy-token",
                                signing_key,
                            )
                        finally:
                            self.assertEqual(https.call_count, 2 if challenge else 1)
                            http.assert_not_called()
