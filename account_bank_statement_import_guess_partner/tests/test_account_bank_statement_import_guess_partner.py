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

    def test_invoice_invoice_origin(self):
        """Test invoice.invoice_origin = transaction["ref"]."""
        self._create_invoice("invoice_origin", REF)
        transaction = self._get_completed_transaction()
        self.assertIn("partner_id", transaction)
        self.assertEqual(transaction["partner_id"], self.partner.id)

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
        self._create_invoice("invoice_origin", "DoesAbsolutelyNotExist")
        transaction = self._get_completed_transaction()
        self.assertNotIn("partner_id", transaction)

    def test_sale_order_name(self):
        """Test sale_order.name = transaction["ref"]."""
        self._create_sale_order("name", REF)
        transaction = self._get_completed_transaction()
        self.assertIn("partner_id", transaction)
        self.assertEqual(transaction["partner_id"], self.partner.id)

    def test_sale_order_client_order_ref(self):
        """Test sale_order.client_order_ref = transaction["ref"]."""
        self._create_sale_order("client_order_ref", REF)
        transaction = self._get_completed_transaction()
        self.assertIn("partner_id", transaction)
        self.assertEqual(transaction["partner_id"], self.partner.id)

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
                "type": "out_invoice",
                "journal_id": self.journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.a_receivable.id,
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 100.00,
                        },
                    )
                ],
            }
        )
        invoice[ref_field] = ref_value  # Might also override name.
        invoice.post()

    def _create_sale_order(self, ref_field, ref_value):
        """Create a sale order with some reference information."""
        sale_order = self.env["sale.order"].create({"partner_id": self.partner.id})
        sale_order[ref_field] = ref_value  # Might also override name.
