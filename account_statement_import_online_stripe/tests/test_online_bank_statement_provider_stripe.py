import io
import json
from datetime import datetime
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon

RETRY_MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe"
)


def _retry_http_error(code, body=None, headers=None):
    return HTTPError(
        "https://api.stripe.com/v1/balance_transactions",
        code,
        "Error",
        headers or {},
        io.BytesIO(json.dumps(body or {}).encode()),
    )


def _retry_response(body):
    return io.BytesIO(json.dumps(body).encode())


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

    def _retry_api_get(self, responses):
        with (
            patch(
                f"{RETRY_MODULE}.urllib.request.urlopen", side_effect=responses
            ) as urlopen,
            patch(f"{RETRY_MODULE}.time.sleep") as sleep,
            mute_logger(RETRY_MODULE),
        ):
            try:
                result = self.provider._stripe_api_get("/balance_transactions")
            except UserError as error:
                result = error
        return result, urlopen, sleep

    def test_retry_rate_limit(self):
        result, urlopen, sleep = self._retry_api_get(
            [
                _retry_http_error(429),
                _retry_http_error(429),
                _retry_response({"data": [], "has_more": False}),
            ]
        )
        self.assertEqual(result, {"data": [], "has_more": False})
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    def test_retry_network_error(self):
        result, urlopen, sleep = self._retry_api_get(
            [URLError("timed out"), _retry_response({"data": [], "has_more": False})]
        )
        self.assertEqual(result, {"data": [], "has_more": False})
        self.assertEqual(urlopen.call_count, 2)

    def test_retry_after_header(self):
        result, urlopen, sleep = self._retry_api_get(
            [
                _retry_http_error(503, headers={"Retry-After": "5"}),
                _retry_response({"data": [], "has_more": False}),
            ]
        )
        self.assertEqual(sleep.call_args.args[0], 5)

    def test_retry_exhausted(self):
        result, urlopen, sleep = self._retry_api_get([_retry_http_error(429)] * 4)
        self.assertIsInstance(result, UserError)
        self.assertEqual(urlopen.call_count, 4)

    def test_no_retry_when_stripe_says_so(self):
        result, urlopen, sleep = self._retry_api_get(
            [_retry_http_error(500, headers={"Stripe-Should-Retry": "false"})]
        )
        self.assertIsInstance(result, UserError)
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    def test_readable_error(self):
        result, urlopen, sleep = self._retry_api_get(
            [
                _retry_http_error(
                    401,
                    body={
                        "error": {
                            "message": "Invalid API Key provided: rk_live_****abcd",
                            "type": "invalid_request_error",
                        }
                    },
                    headers={"Request-Id": "req_123"},
                )
            ]
        )
        self.assertIsInstance(result, UserError)
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(
            str(result),
            "Stripe API call failed: /balance_transactions: Invalid API Key "
            "provided: rk_live_****abcd (type: invalid_request_error, "
            "request: req_123)",
        )
