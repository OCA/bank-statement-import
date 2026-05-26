# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Tecnativa - Pedro M. Baeza
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from os import path

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.account_statement_import_sheet_file.tests import (
    test_account_statement_import_sheet_file,
)


class TestAccountStatementImportSheetFileXlsx(
    test_account_statement_import_sheet_file.TestAccountStatementImportSheetFile
):
    def _get_file_path(self, filename):
        return path.join(path.dirname(__file__), filename)

    def test_import_xlsx_file(self):
        wizard = self._get_import_wizard("fixtures/sample_statement_en.xlsx")
        wizard.import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)

    def test_import_empty_xlsx_file(self):
        wizard = self._get_import_wizard("fixtures/empty_statement_en.xlsx")
        with self.assertRaises(UserError):
            wizard.import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 0)

    def test_metadata_separated_debit_credit_xlsx(self):
        self.sample_statement_map.write(
            {
                "footer_lines_skip_count": 1,
                "header_lines_skip_count": 5,
                "amount_column": None,
                "partner_name_column": None,
                "bank_account_column": None,
                "float_thousands_sep": "none",
                "float_decimal_sep": "comma",
                "timestamp_format": "%m/%d/%y",
                "original_currency_column": None,
                "original_amount_column": None,
                "amount_type": "distinct_credit_debit",
                "amount_debit_column": "Debit",
                "amount_credit_column": "Credit",
            }
        )
        wizard = self._get_import_wizard(
            "fixtures/meta_data_separated_credit_debit.xlsx"
        )
        wizard.import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 4)
        line1 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 1")
        line4 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 4")
        self.assertEqual(line1.amount, 50)
        self.assertEqual(line4.amount, -1300)

    def test_import_xlsx_empty_values(self):
        sample_statement_map_empty_values = (
            self.AccountStatementImportSheetMapping.create(
                {
                    "name": "Sample Statement with empty values",
                    "amount_type": "distinct_credit_debit",
                    "float_decimal_sep": "comma",
                    "delimiter": "n/a",
                    "no_header": 0,
                    "footer_lines_skip_count": 1,
                    "amount_inverse_sign": 0,
                    "header_lines_skip_count": 1,
                    "quotechar": '"',
                    "float_thousands_sep": "dot",
                    "reference_column": "REF",
                    "description_column": "DESCRIPTION",
                    "amount_credit_column": "DEBIT",
                    "amount_debit_column": "CREDIT",
                    "balance_column": "BALANCE",
                    "timestamp_format": "%d/%m/%Y",
                    "timestamp_column": "DATE",
                }
            )
        )
        wizard = self._get_import_wizard(
            "fixtures/sample_statement_en_empty_values.xlsx"
        )
        wizard.sheet_mapping_id = sample_statement_map_empty_values.id
        wizard.import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 3)

    @mute_logger(
        "odoo.addons.account_statement_import_sheet_file.models."
        "account_statement_import"
    )
    def test_offsets(self):
        journal = self.journal
        file_name = "fixtures/sample_statement_offsets.xlsx"
        data = self._data_file(file_name)
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": file_name,
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        # First try with incorrect values
        with self.assertRaises(UserError):
            wizard.with_context(
                account_statement_import_txt_xlsx_test=True
            ).import_file_button()
        self.sample_statement_map.write(
            {"offset_column": 1, "header_lines_skip_count": 3}
        )
        wizard.with_context(
            account_statement_import_txt_xlsx_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_start, 0.0)
        self.assertEqual(statement.balance_end_real, 1491.5)
        self.assertEqual(statement.balance_end, 1491.5)
