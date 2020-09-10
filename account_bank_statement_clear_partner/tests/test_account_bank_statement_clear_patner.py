# Copyright 2020 Tecnativa - João Marques
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from odoo.tests import common


class TestAccountBankStatementClearPartner(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestAccountBankStatementClearPartner, cls).setUpClass()
        cls.partner_1 = cls.env['res.partner'].create(
            {
                "name": "Partner 1",
            }
        )
        cls.partner_2 = cls.env['res.partner'].create(
            {
                "name": "Partner 2",
            }
        )
        cls.account_type_1 = cls.env['account.account.type'].create({
            "name": "Test Account Type 1",
            "type": "other"
        })
        cls.account_1 = cls.env['account.account'].create({
            "name": "Test Account 1",
            "code": "AAAAAAAAAAAAAAAA",
            "user_type_id": cls.account_type_1.id,
        })
        cls.sequence_1 = cls.env['ir.sequence'].create({
            "name": "Test Sequence 1",
        })
        cls.journal_1 = cls.env['account.journal'].create({
            "name": "Test Journal 1",
            "type": "bank",
            "sequence_id": cls.sequence_1.id,
        })
        cls.statement_1 = cls.env["account.bank.statement"].create({
            "name": "Test Bank Statement 1",
            "journal_id": cls.journal_1.id,
        })
        cls.account_move_1 = cls.env["account.move"].create({
            "name": "Test Account Move 1",
            "journal_id": cls.journal_1.id,
        })
        cls.account_move_line_1 = cls.env["account.move.line"].create({
            "move_id": cls.account_move_1.id,
            "account_id": cls.account_1.id,
        })
        line_obj = cls.env["account.bank.statement.line"]
        cls.st_line_w_partner_not_reconciled = line_obj.create({
            "name": "Test Account Bank Statement 1",
            "statement_id": cls.statement_1.id,
            "partner_id": cls.partner_1.id,
            "journal_entry_ids": False,
            "account_id": False,
        })
        cls.st_line_wo_partner_not_reconciled = line_obj.create({
            "name": "Test Account Bank Statement 2",
            "statement_id": cls.statement_1.id,
            "partner_id": False,
            "journal_entry_ids": False,
            "account_id": False,
        })
        cls.st_line_w_partner_reconciled = line_obj.create({
            "name": "Test Account Bank Statement 3",
            "statement_id": cls.statement_1.id,
            "partner_id": cls.partner_2.id,
        })
        cls.account_move_line_1.write({
            "statement_line_id": cls.st_line_w_partner_reconciled.id,
        })

    def test_bank_statements_clear_partner(self):
        self.statement_1.clear_partners()
        # Confirm statement_line_1 has no parter
        self.assertFalse(
            self.st_line_w_partner_not_reconciled.partner_id
        )
        # Confirm statement_line_3 still has partner because it was already reconciled
        self.assertTrue(
            self.st_line_w_partner_reconciled.partner_id
        )
