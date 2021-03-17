# Copyright 2020 Camptocamp SA
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo.tests.common import SavepointCase


class TestGenerateBankStatement(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL77ABNA0574908765",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998748",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank Journal - (test camt)",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": bank.id,
            }
        )

    def _load_statement(self):
        """Load fake statements, to test creation of extra line."""
        absi = self.env["account.bank.statement.import"].create(
            {"attachment_ids": [(0, 0, {"name": "test file", "datas": b""})]}
        )
        absi.with_context(
            {"account_bank_statement_import_transfer_move": True}
        ).import_file()
        bank_st_record = self.env["account.bank.statement"].search(
            [("name", "=", "1234Test/1")], limit=1
        )
        statement_lines = bank_st_record.line_ids
        return statement_lines

    def test_statement_import(self):
        self.journal.transfer_line = True
        lines = self._load_statement()
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(sum(lines.mapped("amount")), 0)
        self.journal.transfer_line = False
        lines = self._load_statement()
        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(sum(lines.mapped("amount")), -754.25)
