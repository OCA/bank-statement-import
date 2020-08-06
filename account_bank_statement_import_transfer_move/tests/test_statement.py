# Copyright 2020 Camptocamp SA
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from unittest.mock import patch

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

    def _parse_file(self, data_file):
        """Fake method for returning valuable data. Extracted from CAMT demo"""
        return (
            None,
            "NL77ABNA0574908765",
            [
                {
                    "balance_end_real": 15121.12,
                    "balance_start": 15568.27,
                    "date": "2014-01-05",
                    "name": "1234Test/1",
                    "transactions": [
                        {
                            "account_number": "NL46ABNA0499998748",
                            "amount": -754.25,
                            "date": "2014-01-05",
                            "name": "Insurance policy 857239PERIOD 01.01.2014 - "
                            "31.12.2014",
                            "note": "MKB Insurance 859239PERIOD 01.01.2014 - "
                            "31.12.2014",
                            "partner_name": "INSURANCE COMPANY TESTX",
                            "ref": "435005714488-ABNO33052620",
                        },
                    ],
                }
            ],
        )

    def _get_bank_statements_available_import_formats(self):
        """Fake method for returning a fake importer for not having errors."""
        return ["test"]

    def _load_statement(self):
        module = "odoo.addons.account_bank_statement_import"
        with patch(
            module
            + ".account_journal.AccountJournal"
            + "._get_bank_statements_available_import_formats",
            self._get_bank_statements_available_import_formats,
        ):
            with patch(
                module
                + ".account_bank_statement_import"
                + ".AccountBankStatementImport._parse_file",
                self._parse_file,
            ):
                self.env["account.bank.statement.import"].create(
                    {"attachment_ids": [(0, 0, {"name": "test file", "datas": b""})]}
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
