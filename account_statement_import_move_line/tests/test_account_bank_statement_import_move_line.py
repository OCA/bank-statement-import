# Copyright 2017 Tecnativa - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from odoo import fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountBankStatementImportMoveLine(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "Test Partner 2"})
        cls.journal_bank = cls.company_data["default_journal_bank"]
        cls.invoice = cls.init_invoice(
            "out_invoice", partner=cls.partner, amounts=[100]
        )
        cls.statement = cls.env["account.bank.statement"].create(
            {"name": "Test account bank statement import move line"}
        )
        cls.statement.journal_id = cls.journal_bank.id

    def test_global(self):
        self.invoice.action_post()
        self.assertTrue(self.invoice.id)
        wizard_o = self.env["account.statement.line.create"]
        context = wizard_o._context.copy()
        context.update(
            {"active_model": "account.bank.statement", "active_id": self.statement.id}
        )
        wizard = wizard_o.with_context(**context).create(
            {
                "statement_id": self.statement.id,
                "partner_id": self.partner.id,
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
