# Copyright 2026 Daniel Lo Nigro <d@d.sb>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountJournal(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.credit_journal = cls.company_data["default_journal_credit"]
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "journal_id": cls.credit_journal.id,
                "service": "dummy",
            }
        )

    def test_open_credit_journal_action_with_statements(self):
        self.provider.create_statement = True
        action = self.credit_journal.open_action()
        self.assertEqual(action["xml_id"], "account.action_credit_statement_tree")
        self.assertEqual(action["res_model"], "account.bank.statement")

    def test_open_credit_journal_action_without_statements(self):
        self.provider.create_statement = False
        action = self.credit_journal.open_action()
        self.assertEqual(
            action["xml_id"],
            "account_reconcile_oca.action_bank_statement_line_reconcile_all",
        )
        self.assertEqual(action["res_model"], "account.bank.statement.line")
