import json
from datetime import datetime, timedelta, timezone
from email.message import Message
from io import BytesIO
from unittest.mock import call, patch
from urllib.error import HTTPError
from urllib.response import addinfourl

from odoo.exceptions import UserError
from odoo.tests.common import new_test_user

from odoo.addons.base.tests.common import BaseCommon


class TestOnlineBankStatementProviderStripe(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "name": "Test Stripe Provider",
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.journal.id,
                "currency_id": cls.env.ref("base.USD").id,
                "stripe_note": "Custom Note {source.object}",
                "stripe_fee_note": "Fee Note {source.object}",
            }
        )

    def _stripe_response(self, status=200, headers=None):
        response_headers = Message()
        for name, value in (headers or {}).items():
            response_headers[name] = value
        response = addinfourl(
            BytesIO(b'{"data": [], "has_more": false}'),
            response_headers,
            "https://api.stripe.com/v1/balance_transactions",
            status,
        )
        response.msg = "test"
        return response

    def test_stripe_api_uses_official_endpoint(self):
        for base in (False, "https://api.stripe.com/v1", "https://api.stripe.com/v1/"):
            with (
                self.subTest(base=base),
                patch("urllib.request.getproxies", return_value={}),
                patch(
                    "urllib.request.HTTPSHandler.https_open",
                    return_value=self._stripe_response(),
                ) as transport,
            ):
                self.provider.api_base = base
                data = self.provider._stripe_api_get(
                    "/balance_transactions", [("limit", 1)]
                )
                transport.assert_called_once()
                request = transport.call_args.args[0]
                self.assertEqual(
                    request.full_url,
                    "https://api.stripe.com/v1/balance_transactions?limit=1",
                )
                self.assertEqual(
                    request.get_header("Authorization"), "Bearer test_api_key"
                )
                self.assertEqual(data, {"data": [], "has_more": False})

    def test_stripe_api_rejects_accountant_endpoint_override(self):
        accountant = new_test_user(
            self.env,
            login="stripe_endpoint_accountant",
            groups="account.group_account_user",
        )
        self.assertFalse(accountant.has_group("base.group_system"))
        provider = self.provider.with_user(accountant)
        for base in (
            "http://127.0.0.1/v1",
            "http://2130706433/v1",
            "http://0x7f000001/v1",
            "http://[::1]/v1",
            "http://169.254.169.254/latest",
            "http://api.stripe.com/v1",
            "https://api.stripe.com:444/v1",
            "https://api.stripe.com.evil.invalid/v1",
            "https://api.stripe.com@evil.invalid/v1",
            "https://evil.invalid@api.stripe.com/v1",
            "https://api.stripe.com/v1?destination=localhost",
            "https://api.stripe.com/v1#fragment",
            "https://api.stripe.com\\@localhost/v1",
            "https://api.stripe.com/v1%2f..%2f",
            "file:///etc",
            "gopher://localhost/v1",
        ):
            with (
                self.subTest(base=base),
                patch("urllib.request.Request") as request,
                patch("urllib.request.build_opener") as opener,
            ):
                provider.api_base = base
                with self.assertRaisesRegex(UserError, "Stripe API base must be"):
                    provider._stripe_api_get("/balance_transactions")
                request.assert_not_called()
                opener.assert_not_called()

    def test_stripe_api_rejects_redirects(self):
        for status in (301, 302, 303, 307, 308):
            for target in ("http://127.0.0.1/private", "https://untrusted.invalid/"):
                with (
                    self.subTest(status=status, target=target),
                    patch("urllib.request.getproxies", return_value={}),
                    patch(
                        "urllib.request.HTTPSHandler.https_open",
                        side_effect=[
                            self._stripe_response(status, {"Location": target}),
                            AssertionError("Redirected HTTPS request"),
                        ],
                    ) as https,
                    patch("urllib.request.HTTPHandler.http_open") as http,
                ):
                    with self.assertRaisesRegex(UserError, "redirects are not allowed"):
                        self.provider._stripe_api_get("/balance_transactions")
                    https.assert_called_once()
                    http.assert_not_called()

    def test_stripe_api_preserves_json_errors(self):
        with (
            patch("urllib.request.getproxies", return_value={}),
            patch(
                "urllib.request.HTTPSHandler.https_open",
                side_effect=HTTPError(
                    "https://api.stripe.com/v1/balance_transactions",
                    401,
                    "Unauthorized",
                    Message(),
                    BytesIO(json.dumps({"error": "invalid key"}).encode()),
                ),
            ),
            self.assertRaisesRegex(UserError, "invalid key"),
        ):
            self.provider._stripe_api_get("/balance_transactions")

    def test_stripe_api_preserves_pagination(self):
        with patch.object(
            type(self.provider),
            "_stripe_api_get",
            side_effect=[
                {"data": [{"id": "first"}], "has_more": True},
                {"data": [{"id": "last"}], "has_more": False},
            ],
        ) as get:
            result = list(
                self.provider._stripe_api_get_all(
                    "/balance_transactions", [("limit", 1)]
                )
            )
            self.assertEqual(result, [{"id": "first"}, {"id": "last"}])
            self.assertEqual(
                get.call_args_list,
                [
                    call("/balance_transactions", params=[("limit", 1)]),
                    call(
                        "/balance_transactions",
                        params=[("limit", 1), ("starting_after", "first")],
                    ),
                ],
            )

    def test_obtain_statement_data_uses_utc_dates(self):
        since = datetime(2026, 1, 14, 23, 15)
        until = datetime(2026, 1, 15, 0, 45)
        for offset in (None, 10, -7):
            with (
                self.subTest(offset=offset),
                patch.object(
                    type(self.provider), "_stripe_api_get_all", return_value=[]
                ) as get_all,
            ):
                date_since, date_until = since, until
                if offset is not None:
                    zone = timezone(timedelta(hours=offset))
                    date_since = since.replace(tzinfo=timezone.utc).astimezone(zone)
                    date_until = until.replace(tzinfo=timezone.utc).astimezone(zone)
                data = self.provider._obtain_statement_data(
                    date_since,
                    date_until,
                )
                get_all.assert_called_once()
                path, params = get_all.call_args.args
                self.assertEqual(path, "/balance_transactions")
                params = dict(params)
                self.assertEqual(params["created[gte]"], 1768432500)
                self.assertEqual(params["created[lt]"], 1768437900)
                self.assertEqual(data, ([], {}))

    def test_obtain_statement_data_success(self):
        mock_stripe_data = {
            "data": [
                {
                    "id": "txn_123",
                    "amount": 10000,
                    "currency": "usd",
                    "created": 1678886400,
                    "object": "balance_transaction",
                    "fee": 100,
                    "type": "transfer",
                    "source": {
                        "id": "ch_123",
                        "object": "charge",
                        "metadata": {"invoice_number": "INV-001"},
                        "payment_method_details": {"type": "card"},
                    },
                },
                {
                    "id": "txn_456",
                    "amount": 20000,
                    "currency": "usd",
                    "created": 1678972800,
                    "object": "balance_transaction",
                    "fee": 200,
                    "type": "transfer",
                    "source": {
                        "id": "ch_456",
                        "object": "charge",
                        "metadata": {"invoice_number": "INV-002"},
                        "payment_method_details": {"type": "card"},
                    },
                },
            ],
            "has_more": False,
        }
        with patch(
            "odoo.addons.account_statement_import_online_stripe.models.online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe._stripe_api_get_all",
            return_value=mock_stripe_data["data"],
        ) as mock_get_all:
            date_since = datetime(2023, 3, 15)
            date_until = datetime(2023, 3, 17)
            statement_data, _ = self.provider._obtain_statement_data(
                date_since, date_until
            )
            mock_get_all.assert_called_once()
            self.assertEqual(len(statement_data), 4)
            for line in statement_data[:2]:
                self.assertEqual(line["date"], datetime(2023, 3, 15, 13, 20))
            for line in statement_data[2:]:
                self.assertEqual(line["date"], datetime(2023, 3, 16, 13, 20))
            self.assertEqual(statement_data[0]["amount"], 100.0)
            self.assertEqual(statement_data[0]["unique_import_id"], "txn_123")
            self.assertEqual(statement_data[0]["ref"], "INV-001")
            self.assertEqual(
                statement_data[0]["payment_ref"], "stripe INV-001 charge ch_123 card"
            )
            self.assertEqual(statement_data[0]["narration"], "Custom Note charge")
            self.assertEqual(statement_data[1]["amount"], -1.0)
            self.assertEqual(statement_data[1]["unique_import_id"], "txn_123_fee")
            self.assertEqual(statement_data[1]["ref"], "")
            self.assertEqual(
                statement_data[1]["payment_ref"],
                "stripe fee INV-001 charge ch_123 card",
            )
            self.assertEqual(statement_data[1]["narration"], "Fee Note charge")
            self.assertEqual(statement_data[2]["amount"], 200.0)
            self.assertEqual(statement_data[2]["unique_import_id"], "txn_456")
            self.assertEqual(statement_data[2]["ref"], "INV-002")
            self.assertEqual(
                statement_data[2]["payment_ref"], "stripe INV-002 charge ch_456 card"
            )
            self.assertEqual(statement_data[2]["narration"], "Custom Note charge")
            self.assertEqual(statement_data[3]["amount"], -2.0)
            self.assertEqual(statement_data[3]["unique_import_id"], "txn_456_fee")
            self.assertEqual(statement_data[3]["ref"], "")
            self.assertEqual(
                statement_data[3]["payment_ref"],
                "stripe fee INV-002 charge ch_456 card",
            )
            self.assertEqual(statement_data[3]["narration"], "Fee Note charge")
