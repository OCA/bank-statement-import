from datetime import datetime
from unittest.mock import patch

from odoo.exceptions import ValidationError

from odoo.addons.base.tests.common import BaseCommon

FEES_MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)


FEES_TRANSACTION = {
    "id": "txn_123",
    "amount": 10000,
    "currency": "usd",
    "created": 1678886400,
    "object": "balance_transaction",
    "fee": 100,
    "type": "charge",
    "source": {"id": "ch_123", "object": "charge"},
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
        cls.fees_journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "SFEE",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.fees_stripe_partner = cls.env["res.partner"].create({"name": "Stripe"})
        cls.fees_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.fees_journal.id,
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

    def _fees_obtain_lines(self):
        with patch(
            f"{FEES_MODULE}._stripe_api_get_all", return_value=[FEES_TRANSACTION]
        ):
            lines, __ = self.fees_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        return lines

    def test_fees_without_partner(self):
        lines = self._fees_obtain_lines()
        self.assertEqual(len(lines), 2)
        for line in lines:
            self.assertNotIn("partner_id", line)
            self.assertNotIn("transaction_type", line)

    def test_fees_as_payments(self):
        self.fees_provider.write(
            {
                "stripe_fee_as_payment": True,
                "stripe_fee_partner_id": self.fees_stripe_partner.id,
            }
        )
        payment_line, fee_line = self._fees_obtain_lines()
        self.assertNotIn("partner_id", payment_line)
        self.assertEqual(fee_line["amount"], -1.0)
        self.assertEqual(fee_line["partner_id"], self.fees_stripe_partner.id)
        self.assertEqual(fee_line["partner_name"], "Stripe")
        self.assertEqual(fee_line["transaction_type"], "fee")

    def test_fees_as_payments_statement_lines(self):
        self.fees_provider.write(
            {
                "stripe_fee_as_payment": True,
                "stripe_fee_partner_id": self.fees_stripe_partner.id,
            }
        )
        with patch(
            f"{FEES_MODULE}._stripe_api_get_all", return_value=[FEES_TRANSACTION]
        ):
            self.fees_provider._pull(datetime(2023, 3, 15), datetime(2023, 3, 16))
        fee_line = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.fees_journal.id), ("amount", "<", 0)]
        )
        self.assertEqual(fee_line.partner_id, self.fees_stripe_partner)
        self.assertEqual(fee_line.transaction_type, "fee")

    def test_fees_as_payments_requires_partner(self):
        with self.assertRaises(ValidationError):
            self.fees_provider.stripe_fee_as_payment = True
