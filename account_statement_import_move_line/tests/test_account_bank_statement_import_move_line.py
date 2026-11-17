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
        context = wizard_o.env.context.copy()
        context.update(
            {"active_model": "account.bank.statement", "active_id": self.statement.id}
        )
        wizard = wizard_o.with_context(**context).create(
            {
                "statement_id": self.statement.id,
                "partner_id": self.partner.id,
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

    def test_move_line_without_due_date(self):
        """Journal items with no due date are selectable, so they must be
        importable: the statement line date falls back on the accounting date.
        """
        misc_move = self.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": self.company_data["default_journal_misc"].id,
                "date": fields.Date.today(),
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "account_id": self.company_data[
                                "default_account_receivable"
                            ].id,
                            "partner_id": self.partner.id,
                            "name": "Receivable without due date",
                            "debit": 50.0,
                            "credit": 0.0,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "account_id": self.company_data[
                                "default_account_revenue"
                            ].id,
                            "partner_id": self.partner.id,
                            "name": "Counterpart",
                            "debit": 0.0,
                            "credit": 50.0,
                        },
                    ),
                ],
            }
        )
        misc_move.action_post()
        move_line = misc_move.line_ids.filtered(
            lambda line: line.account_id
            == self.company_data["default_account_receivable"]
        )
        self.assertFalse(move_line.date_maturity)
        wizard = (
            self.env["account.statement.line.create"]
            .with_context(
                active_model="account.bank.statement", active_id=self.statement.id
            )
            .create(
                {
                    "statement_id": self.statement.id,
                    "partner_id": self.partner.id,
                    "date_type": "due",
                    "due_date": fields.Date.today(),
                    "invoice": False,
                }
            )
        )
        wizard.populate()
        self.assertIn(move_line, wizard.move_line_ids)
        wizard.move_line_ids = move_line
        wizard.create_statement_lines()
        statement_line = self.statement.line_ids.filtered(
            lambda line: line.payment_ref == "Receivable without due date"
        )
        self.assertEqual(len(statement_line), 1)
        self.assertEqual(statement_line.date, move_line.date)
        self.assertEqual(statement_line.amount, 50.0)
