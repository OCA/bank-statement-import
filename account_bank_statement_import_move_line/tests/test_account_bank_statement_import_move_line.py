# Copyright 2017 Tecnativa - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from odoo import fields
from odoo.tests import common


class TestAccountBankStatementImportMoveLine(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestAccountBankStatementImportMoveLine, cls).setUpClass()

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
        cls.invoice = cls.env["account.move"].create(
            {
                "name": "Test Invoice 3",
                "partner_id": cls.partner.id,
                "type": "out_invoice",
                "journal_id": cls.journal.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": cls.a_receivable.id,
                            "name": "Test line",
                            "quantity": 1.0,
                            "price_unit": 100.00,
                        },
                    )
                ],
            }
        )
        cls.statement = cls.env["account.bank.statement"].create(
            {"journal_id": cls.journal.id}
        )

    def test_global(self):
        self.invoice.post()
        self.assertTrue(self.invoice.id)
        wizard_o = self.env["account.statement.line.create"]
        context = wizard_o._context.copy()
        context.update(
            {"active_model": "account.bank.statement", "active_id": self.statement.id}
        )
        wizard = wizard_o.with_context(context).create(
            {
                "statement_id": self.statement.id,
                "partner_id": self.partner.id,
                "journal_ids": [(4, self.journal.id)],
                "allow_blocked": True,
                "date_type": "move",
                "move_date": fields.Date.today(),
                "invoice": False,
            }
        )
        wizard.populate()
        self.assertEqual(len(wizard.move_line_ids), 1)
        line = wizard.move_line_ids
        self.assertEqual(line.debit, self.invoice.amount_total)
        wizard.create_statement_lines()
        line = self.statement.line_ids[0]
        self.assertEqual(line.amount, self.invoice.amount_total)
