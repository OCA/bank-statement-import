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


BILLING_MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)


BILLING_CUSTOMER = {"id": "cus_1", "object": "customer", "email": "jane@example.com"}


BILLING_SUBSCRIPTION = {"id": "sub_1", "object": "subscription", "status": "active"}


def _billing_http_error(path, code):
    """The error raised by _stripe_api_get when Stripe answers with an error"""
    error = UserError(path)
    error.__cause__ = HTTPError(path, code, "", {}, None)
    return error


def _billing_transaction(charge, tx_id="txn_1"):
    return {
        "id": tx_id,
        "amount": 1000,
        "currency": "usd",
        "created": 1678886400,
        "object": "balance_transaction",
        "fee": 0,
        "type": "charge",
        "source": charge,
    }


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
        journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "SBILL",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.billing_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": journal.id,
                "stripe_fetch_billing": True,
                "stripe_label": "{invoice.number} {subscription.id} {customer.email}",
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

    def _billing_obtain_lines(self, transactions, objects):
        """Pull the transactions, Stripe answering with the given objects"""
        calls = []

        def api_get(provider, path, params=None, data=None):
            calls.append(path)
            if path not in objects:
                raise _billing_http_error(path, 404)
            return objects[path]

        with (
            patch(f"{BILLING_MODULE}._stripe_api_get_all", return_value=transactions),
            patch(f"{BILLING_MODULE}._stripe_api_get", api_get),
        ):
            lines, __ = self.billing_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        return lines, calls

    def test_billing_current_api(self):
        """Invoice from the invoice payments, subscription from its parent"""
        charge = {
            "id": "ch_1",
            "object": "charge",
            "customer": "cus_1",
            "payment_intent": "pi_1",
        }
        invoice = {
            "id": "in_1",
            "number": "INV-1",
            "parent": {"subscription_details": {"subscription": "sub_1"}},
        }
        lines, calls = self._billing_obtain_lines(
            [_billing_transaction(charge)],
            {
                "/customers/cus_1": BILLING_CUSTOMER,
                "/invoice_payments": {"data": [{"invoice": invoice}]},
                "/subscriptions/sub_1": BILLING_SUBSCRIPTION,
            },
        )
        self.assertEqual(lines[0]["payment_ref"], "INV-1 sub_1 jane@example.com")
        raw_data = json.loads(lines[0]["raw_data"])
        self.assertEqual(raw_data["subscription"]["status"], "active")
        self.assertEqual(
            calls, ["/customers/cus_1", "/invoice_payments", "/subscriptions/sub_1"]
        )

    def test_billing_old_api(self):
        """Before 2025-03-31.basil the charge links its invoice"""
        charge = {
            "id": "ch_1",
            "object": "charge",
            "customer": None,
            "invoice": "in_1",
            "payment_intent": "pi_1",
        }
        lines, calls = self._billing_obtain_lines(
            [_billing_transaction(charge)],
            {
                "/invoices/in_1": {
                    "id": "in_1",
                    "number": "INV-1",
                    "subscription": "sub_1",
                },
                "/subscriptions/sub_1": BILLING_SUBSCRIPTION,
            },
        )
        self.assertEqual(lines[0]["payment_ref"], "INV-1 sub_1 ")
        self.assertEqual(calls, ["/invoices/in_1", "/subscriptions/sub_1"])

    def test_billing_old_api_without_invoice(self):
        """A charge without invoice needs no request"""
        charge = {"id": "ch_1", "object": "charge", "invoice": None}
        lines, calls = self._billing_obtain_lines([_billing_transaction(charge)], {})
        self.assertEqual(calls, [])

    def test_billing_missing_objects_and_cache(self):
        """Objects not found are left out, and each object is asked once"""
        charge = {
            "id": "ch_1",
            "object": "charge",
            "customer": "cus_deleted",
            "payment_intent": "pi_1",
        }
        lines, calls = self._billing_obtain_lines(
            [
                _billing_transaction(charge),
                _billing_transaction(dict(charge, id="ch_2"), "txn_2"),
            ],
            {"/invoice_payments": {"data": []}},
        )
        self.assertEqual(len(lines), 2)
        self.assertNotIn("customer", json.loads(lines[0]["raw_data"]))
        self.assertEqual(calls, ["/customers/cus_deleted", "/invoice_payments"])

    def test_billing_other_errors_are_raised(self):
        charge = {"id": "ch_1", "object": "charge", "customer": "cus_1"}

        def api_get(provider, path, params=None, data=None):
            raise _billing_http_error(path, 500)

        with (
            patch(
                f"{BILLING_MODULE}._stripe_api_get_all",
                return_value=[_billing_transaction(charge)],
            ),
            patch(f"{BILLING_MODULE}._stripe_api_get", api_get),
            self.assertRaises(UserError),
        ):
            self.billing_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )

    def test_billing_disabled(self):
        self.billing_provider.stripe_fetch_billing = False
        charge = {"id": "ch_1", "object": "charge", "customer": "cus_1"}
        lines, calls = self._billing_obtain_lines([_billing_transaction(charge)], {})
        self.assertEqual(calls, [])

    def test_billing_not_a_payment(self):
        payout = {"id": "po_1", "object": "payout"}
        lines, calls = self._billing_obtain_lines([_billing_transaction(payout)], {})
        self.assertEqual(calls, [])
