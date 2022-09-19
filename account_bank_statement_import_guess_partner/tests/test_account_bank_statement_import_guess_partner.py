# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0
"""Test determining partner from ref in transaction."""
from odoo.tests import common

REF = "SO0001"
STMTS_VALS = [
    {
        "name": "Test000123",
        "date": "2022-03-29",
        "transactions": [
            {
                "name": "Bla000123",
                "date": "2022-03-30",
                "amount": 23.95,
                "unique_import_id": "random0001",
                "ref": REF,
            },
        ],
    }
]


class TestAccountBankStatementImportGuessPartner(common.SavepointCase):
    """Test determining partner from ref in transaction."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.account_type = cls.env["account.account.type"].create(
            {"name": "Test Account Type", "type": "other", "internal_group": "asset"}
        )
        cls.a_receivable = cls.env["account.account"].create(
            {
                "code": "TAA",
                "name": "Test Receivable Account",
                "internal_type": "receivable",
                "user_type_id": cls.account_type.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {"name": "Test Partner 2", "parent_id": False}
        )
        cls.journal = cls.env["account.journal"].create(
            {"name": "Test Journal", "type": "sale", "code": "TJS0"}
        )

    def test_invoice_ref(self):
        """Test invoice.ref = transaction["ref"]."""
        self._create_invoice("ref", REF)
        transaction = self._get_completed_transaction()
        self.assertIn("partner_id", transaction)
        self.assertEqual(transaction["partner_id"], self.partner.id)

    def test_invoice_name(self):
        """Test invoice.name = transaction["ref"]."""
        self._create_invoice("name", REF)
        transaction = self._get_completed_transaction()
        self.assertIn("partner_id", transaction)
        self.assertEqual(transaction["partner_id"], self.partner.id)

    def test_invoice_unknown_ref(self):
        """Test no value in invoice for transaction["ref"]."""
        self._create_invoice("ref", "DoesAbsolutelyNotExist")
        transaction = self._get_completed_transaction()
        self.assertNotIn("partner_id", transaction)

    def _get_completed_transaction(self):
        """Complete statements and return first transaction in first statement."""
        # pylint: disable=protected-access
        absi_model = self.env["account.bank.statement.import"]
        # Make sure dictionary is "incompleted".
        transaction = STMTS_VALS[0]["transactions"][0]
        if "partner_id" in transaction:
            del transaction["partner_id"]
        absi_model._complete_stmts_vals(STMTS_VALS, self.journal, "BNK0001")
        return transaction

    def _create_invoice(self, ref_field, ref_value):
        """Create an invoice with some reference information."""
        invoice = self.env["account.move"].create(
            {
                "name": "Test Invoice 3",
                "partner_id": self.partner.id,
                "journal_id": self.journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.a_receivable.id,
                            "name": "Test line",
                            "quantity": 1.0,
                        },
                    )
                ],
            }
        )
        invoice[ref_field] = ref_value  # Might also override name.
        invoice.post()
