# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from datetime import datetime
from unittest.mock import patch
from urllib.error import HTTPError

from odoo.exceptions import UserError

from odoo.addons.base.tests.common import BaseCommon

MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)

CUSTOMER = {"id": "cus_1", "object": "customer", "email": "jane@example.com"}
SUBSCRIPTION = {"id": "sub_1", "object": "subscription", "status": "active"}


def _http_error(path, code):
    """The error raised by _stripe_api_get when Stripe answers with an error"""
    error = UserError(path)
    error.__cause__ = HTTPError(path, code, "", {}, None)
    return error


def _transaction(charge, tx_id="txn_1"):
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


class TestStripeBilling(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "STRP",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": journal.id,
                "stripe_fetch_billing": True,
                "stripe_label": "{invoice.number} {subscription.id} {customer.email}",
            }
        )

    def _obtain_lines(self, transactions, objects):
        """Pull the transactions, Stripe answering with the given objects"""
        calls = []

        def api_get(provider, path, params=None, data=None):
            calls.append(path)
            if path not in objects:
                raise _http_error(path, 404)
            return objects[path]

        with (
            patch(f"{MODULE}._stripe_api_get_all", return_value=transactions),
            patch(f"{MODULE}._stripe_api_get", api_get),
        ):
            lines, __ = self.provider._obtain_statement_data(
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
        lines, calls = self._obtain_lines(
            [_transaction(charge)],
            {
                "/customers/cus_1": CUSTOMER,
                "/invoice_payments": {"data": [{"invoice": invoice}]},
                "/subscriptions/sub_1": SUBSCRIPTION,
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
        lines, calls = self._obtain_lines(
            [_transaction(charge)],
            {
                "/invoices/in_1": {
                    "id": "in_1",
                    "number": "INV-1",
                    "subscription": "sub_1",
                },
                "/subscriptions/sub_1": SUBSCRIPTION,
            },
        )
        self.assertEqual(lines[0]["payment_ref"], "INV-1 sub_1 ")
        self.assertEqual(calls, ["/invoices/in_1", "/subscriptions/sub_1"])

    def test_billing_old_api_without_invoice(self):
        """A charge without invoice needs no request"""
        charge = {"id": "ch_1", "object": "charge", "invoice": None}
        lines, calls = self._obtain_lines([_transaction(charge)], {})
        self.assertEqual(calls, [])

    def test_billing_missing_objects_and_cache(self):
        """Objects not found are left out, and each object is asked once"""
        charge = {
            "id": "ch_1",
            "object": "charge",
            "customer": "cus_deleted",
            "payment_intent": "pi_1",
        }
        lines, calls = self._obtain_lines(
            [_transaction(charge), _transaction(dict(charge, id="ch_2"), "txn_2")],
            {"/invoice_payments": {"data": []}},
        )
        self.assertEqual(len(lines), 2)
        self.assertNotIn("customer", json.loads(lines[0]["raw_data"]))
        self.assertEqual(calls, ["/customers/cus_deleted", "/invoice_payments"])

    def test_billing_other_errors_are_raised(self):
        charge = {"id": "ch_1", "object": "charge", "customer": "cus_1"}

        def api_get(provider, path, params=None, data=None):
            raise _http_error(path, 500)

        with (
            patch(f"{MODULE}._stripe_api_get_all", return_value=[_transaction(charge)]),
            patch(f"{MODULE}._stripe_api_get", api_get),
            self.assertRaises(UserError),
        ):
            self.provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )

    def test_billing_disabled(self):
        self.provider.stripe_fetch_billing = False
        charge = {"id": "ch_1", "object": "charge", "customer": "cus_1"}
        lines, calls = self._obtain_lines([_transaction(charge)], {})
        self.assertEqual(calls, [])

    def test_billing_not_a_payment(self):
        payout = {"id": "po_1", "object": "payout"}
        lines, calls = self._obtain_lines([_transaction(payout)], {})
        self.assertEqual(calls, [])
