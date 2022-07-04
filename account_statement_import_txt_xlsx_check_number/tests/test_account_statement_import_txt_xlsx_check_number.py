# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from os import path

from odoo.tests import common


class TestAccountBankStatementImportTxtXlsxCheckNumber(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.currency_usd = self.env.ref("base.USD")
        self.sample_statement_map = self.env.ref(
            "account_statement_import_txt_xlsx.sample_statement_map"
        )
        self.AccountJournal = self.env["account.journal"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountStatementImport = self.env["account.statement.import"]
        self.AccountStatementImportSheetMapping = self.env[
            "account.statement.import.sheet.mapping"
        ]
        self.AccountStatementImportSheetMappingWizard = self.env[
            "account.statement.import.sheet.mapping.wizard"
        ]

    def _data_file(self, filename, encoding=None):
        mode = "rt" if encoding else "rb"
        with open(path.join(path.dirname(__file__), filename), mode) as file:
            data = file.read()
            if encoding:
                data = data.encode(encoding)
            return b64encode(data)

    def test_check_number(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
            }
        )
        data = self._data_file("fixtures/sample_statement.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/sample_statement.csv",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_txt_xlsx_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)
        self.assertEqual(statement.line_ids.check_number, "00001")
