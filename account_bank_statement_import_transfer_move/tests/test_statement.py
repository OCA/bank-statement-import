# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
import unittest

from odoo.modules.module import get_module_resource
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
        module = self.env["ir.module.module"].search(
            [
                ("name", "=", "account_bank_statement_import_camt_oca"),
                ("state", "=", "installed"),
            ]
        )
        if not (module):
            raise unittest.SkipTest(
                "account_bank_statement_import_camt_oca module is not installed"
            )

        testfile = get_module_resource(
            "account_bank_statement_import_camt_oca", "test_files", "test-camt053"
        )
        with open(testfile, "rb") as datafile:
            camt_file = base64.b64encode(datafile.read())

            self.env["account.bank.statement.import"].create(
                {"attachment_ids": [(0, 0, {"name": "test file", "datas": camt_file})]}
            ).import_file()

            bank_st_record = self.env["account.bank.statement"].search(
                [("name", "=", "1234Test/1")], limit=1
            )
            statement_lines = bank_st_record.line_ids

            return statement_lines

    def test_statement_import(self):

        self.journal.transfer_line = True
        lines = self._load_statement()
        self.assertEqual(len(lines), 5)
        self.assertAlmostEqual(sum(lines.mapped("amount")), 0)

        self.journal.transfer_line = False
        lines = self._load_statement()
        self.assertEqual(len(lines), 4)
        self.assertAlmostEqual(sum(lines.mapped("amount")), -12.99)
