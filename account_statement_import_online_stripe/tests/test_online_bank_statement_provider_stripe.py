from datetime import datetime
from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon

from ..models.online_bank_statement_provider_stripe import _stripe_payment_keys

ODOO_MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)


def _odoo_transaction(tx_id, charge_id, payment_intent_id):
    return {
        "id": tx_id,
        "amount": 1000,
        "currency": "usd",
        "created": 1678886400,
        "object": "balance_transaction",
        "fee": 50,
        "type": "charge",
        "source": {
            "id": charge_id,
            "object": "charge",
            "payment_intent": payment_intent_id,
        },
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
        cls.odoo_journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "SODOO",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.odoo_partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.odoo_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.odoo_journal.id,
                "stripe_skip_website_payments": True,
            }
        )
        cls.odoo_transactions = [
            _odoo_transaction("txn_1", "ch_1", "pi_1"),
            _odoo_transaction("txn_2", "ch_2", "pi_2"),
            _odoo_transaction("txn_3", "ch_3", "pi_3"),
        ]

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

    def _odoo_obtain_lines(self, odoo_payments, line_values):
        with (
            patch(
                f"{ODOO_MODULE}._stripe_api_get_all",
                return_value=self.odoo_transactions,
            ),
            patch(
                f"{ODOO_MODULE}._stripe_get_odoo_payments", return_value=odoo_payments
            ),
            patch(
                f"{ODOO_MODULE}._stripe_odoo_payment_line_values",
                side_effect=lambda payment: line_values[payment],
            ),
        ):
            lines, __ = self.odoo_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        return {line["unique_import_id"]: line for line in lines}

    def test_payment_keys(self):
        self.assertEqual(
            _stripe_payment_keys(self.odoo_transactions[0]), {"ch_1", "pi_1"}
        )
        # A refund refers to the payment intent of the payment it refunds: not a
        # key of the refund
        refund = _odoo_transaction("txn_4", "re_1", "pi_1")
        refund["source"]["object"] = "refund"
        self.assertEqual(_stripe_payment_keys(refund), {"re_1"})

    def test_payments_recorded_by_odoo(self):
        lines = self._odoo_obtain_lines(
            {"pi_1": "posted on the journal", "ch_2": "to reconcile"},
            {
                "posted on the journal": None,
                "to reconcile": {"partner_id": self.odoo_partner.id},
            },
        )
        # Already posted on the journal: only its fee is imported
        self.assertNotIn("txn_1", lines)
        self.assertIn("txn_1_fee", lines)
        # Recorded elsewhere: imported with the partner of the payment
        self.assertEqual(lines["txn_2"]["partner_id"], self.odoo_partner.id)
        self.assertNotIn("partner_id", lines["txn_2_fee"])
        # Not recorded by Odoo: imported as usual
        self.assertNotIn("partner_id", lines["txn_3"])

    def test_option_disabled(self):
        self.odoo_provider.stripe_skip_website_payments = False
        with (
            patch(
                f"{ODOO_MODULE}._stripe_api_get_all",
                return_value=self.odoo_transactions,
            ),
            patch(f"{ODOO_MODULE}._stripe_get_odoo_payments") as get_odoo_payments,
        ):
            lines, __ = self.odoo_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        get_odoo_payments.assert_not_called()
        self.assertEqual(len(lines), 6)

    def test_odoo_payments_search(self):
        """With the Stripe payment provider, find the done transactions"""
        if "payment.transaction" not in self.env:
            self.skipTest("The Payment module is not installed")
        stripe = self.env["payment.provider"].search([("code", "=", "stripe")], limit=1)
        if not stripe:
            self.skipTest("The Stripe payment provider is not installed")
        method = (
            self.env["payment.method"]
            .with_context(active_test=False)
            .search([("code", "=", "card")], limit=1)
        )
        values = {
            "provider_id": stripe.id,
            "payment_method_id": method.id,
            "amount": 10.0,
            "currency_id": self.env.ref("base.USD").id,
            "partner_id": self.odoo_partner.id,
        }
        done, pending = self.env["payment.transaction"].create(
            [
                dict(values, reference="T1", provider_reference="pi_1", state="done"),
                dict(values, reference="T2", provider_reference="pi_2"),
            ]
        )
        odoo_payments = self.odoo_provider._stripe_get_odoo_payments(
            self.odoo_transactions
        )
        self.assertEqual(odoo_payments, {"pi_1": done})
        # Without a payment posted on the journal, the line gets the partner
        self.assertEqual(
            self.odoo_provider._stripe_odoo_payment_line_values(done),
            {"partner_id": self.odoo_partner.id},
        )
        if "payment_id" not in done._fields:
            return
        # Payment posted directly on the account of the journal: line skipped
        method_line = self.odoo_journal.inbound_payment_method_line_ids[:1]
        method_line.payment_account_id = self.odoo_journal.default_account_id
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.odoo_partner.id,
                "amount": 10.0,
                "journal_id": self.odoo_journal.id,
                "payment_method_line_id": method_line.id,
            }
        )
        payment.action_post()
        done.payment_id = payment
        self.assertIsNone(self.odoo_provider._stripe_odoo_payment_line_values(done))
