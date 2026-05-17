# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo.tests.common import TransactionCase


class TestAccountStatementLineOrder(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        cls.currency = cls.env.company.currency_id
        cls.bank_journal = cls.env.company.bank_journal_ids[0]
        cls.partner = cls.env["res.partner"].create({"name": "Tester"})
        # Create 2 bank statements for the same day
        cls.statement1 = cls.env["account.bank.statement"].create(
            {
                "name": "20250521120000121345",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "date": "2025-05-21",
                            "payment_ref": "line_0_1",
                            "partner_id": cls.partner.id,
                            "foreign_currency_id": cls.currency.id,
                            "journal_id": cls.bank_journal.id,
                            "amount": 1250.0,
                            "sequence": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "date": "2025-05-21",
                            "payment_ref": "line_0_2",
                            "partner_id": cls.partner.id,
                            "foreign_currency_id": cls.currency.id,
                            "journal_id": cls.bank_journal.id,
                            "amount": 1350.0,
                            "sequence": 2,
                        },
                    ),
                ],
            }
        )
        cls.statement2 = cls.env["account.bank.statement"].create(
            {
                "name": "20250521120000121455",
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "date": "2025-05-21",
                            "payment_ref": "line_1_1",
                            "partner_id": cls.partner.id,
                            "foreign_currency_id": cls.currency.id,
                            "journal_id": cls.bank_journal.id,
                            "amount": 250.0,
                            "sequence": 1,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "date": "2025-05-21",
                            "payment_ref": "line_1_2",
                            "partner_id": cls.partner.id,
                            "foreign_currency_id": cls.currency.id,
                            "journal_id": cls.bank_journal.id,
                            "amount": 350.0,
                            "sequence": 2,
                        },
                    ),
                ],
            }
        )
        cls.statements = cls.statement1 | cls.statement2

    def test_internal_index_group_statement_together(self):
        """Check using the custom internal index computation.

        The statement lines are grouped by statement in the
        default order.

        """
        self.bank_journal.statement_line_internal_index = (
            "date_statement_id_line_sequence_id"
        )
        lines = self.env["account.bank.statement.line"].search(
            [("statement_id", "in", self.statements.ids)]
        )
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].payment_ref, "line_1_1")
        self.assertEqual(lines[1].payment_ref, "line_1_2")
        self.assertEqual(lines[2].payment_ref, "line_0_1")
        self.assertEqual(lines[3].payment_ref, "line_0_2")

    def test_default_internal_index_computation(self):
        """Check using the default internal index computation.

        The statement lines are not grouped by statement, it is the
        sequence on the line that is ordering multiple line for
        the same day.

        """
        self.bank_journal.statement_line_internal_index = "date_line_sequence_id"
        lines = self.env["account.bank.statement.line"].search(
            [("statement_id", "in", self.statements.ids)]
        )
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].payment_ref, "line_1_1")
        self.assertEqual(lines[1].payment_ref, "line_0_1")
        self.assertEqual(lines[2].payment_ref, "line_1_2")
        self.assertEqual(lines[3].payment_ref, "line_0_2")
