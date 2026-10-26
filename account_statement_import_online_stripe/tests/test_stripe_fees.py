# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon

MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)

TRANSACTION = {
    "id": "txn_123",
    "amount": 10000,
    "currency": "usd",
    "created": 1678886400,
    "object": "balance_transaction",
    "fee": 100,
    "type": "charge",
    "source": {"id": "ch_123", "object": "charge"},
}


class TestStripeFees(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "STRP",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.stripe_partner = cls.env["res.partner"].create({"name": "Stripe"})
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.journal.id,
            }
        )

    def _obtain_lines(self):
        with patch(f"{MODULE}._stripe_api_get_all", return_value=[TRANSACTION]):
            lines, __ = self.provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        return lines

    def test_fees_without_partner(self):
        lines = self._obtain_lines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertNotIn("partner_id", line)
            self.assertNotIn("transaction_type", line)

    def test_fees_as_payments(self):
        self.provider.write(
            {
                "stripe_fee_as_payment": True,
                "stripe_fee_partner_id": self.stripe_partner.id,
            }
        )
        payment_line, fee_line = self._obtain_lines()
        self.assertNotIn("partner_id", payment_line)
        self.assertEqual(fee_line["amount"], -1.0)
        self.assertEqual(fee_line["partner_id"], self.stripe_partner.id)
        self.assertEqual(fee_line["partner_name"], "Stripe")
        self.assertEqual(fee_line["transaction_type"], "fee")

    def test_fees_as_payments_statement_lines(self):
        self.provider.write(
            {
                "stripe_fee_as_payment": True,
                "stripe_fee_partner_id": self.stripe_partner.id,
            }
        )
        with patch(f"{MODULE}._stripe_api_get_all", return_value=[TRANSACTION]):
            self.provider._pull(datetime(2023, 3, 15), datetime(2023, 3, 16))
        fee_line = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.journal.id), ("amount", "<", 0)]
        )
        self.assertEqual(fee_line.partner_id, self.stripe_partner)
        self.assertEqual(fee_line.transaction_type, "fee")

    def test_fees_as_payments_requires_partner(self):
        with self.assertRaises(ValidationError):
            self.provider.stripe_fee_as_payment = True
