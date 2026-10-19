# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Tecnativa - Pedro M. Baeza
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from datetime import datetime
from io import BytesIO
from os import path

import openpyxl

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

    def test_import_xlsx_numeric_amounts_with_comma_decimal_sep(self):
        """Numeric cells must not be reinterpreted through the mapping seps.

        Amounts stored as numbers carry no separators: the sheet only holds a
        display format, which never reaches the parser. Rendering them as text
        printed a dot decimal, so a mapping set to a comma decimal separator
        dropped it and shifted the amount by a factor of 10 or 100 depending on
        how many decimals the value had.
        """
        self.sample_statement_map.write(
            {
                "float_thousands_sep": "none",
                "float_decimal_sep": "comma",
                "original_currency_column": None,
                "original_amount_column": None,
                "partner_name_column": None,
                "bank_account_column": None,
                "reference_column": "Reference",
            }
        )
        workbook = openpyxl.Workbook()
        sheet = workbook.active
        sheet.append(["Date", "Label", "Reference", "Amount"])
        # Amounts as native numbers, with a display format that shows a comma
        # decimal separator -- exactly what the mapping is configured for. The
        # reference is numeric too, to cover a non-amount column that stops
        # being handed over as text.
        for label, reference, amount in [
            ("TWO DECIMALS", 26182, 1234.56),
            ("ONE DECIMAL", 289400, 78.9),
            ("NO DECIMALS", 304102, 100),
        ]:
            sheet.append([datetime(2026, 7, 1), label, reference, amount])
            sheet.cell(row=sheet.max_row, column=4).number_format = "#.##0,00"
        buffer = BytesIO()
        workbook.save(buffer)
        wizard = self.AccountStatementImport.with_context(
            journal_id=self.journal.id, account_statement_import_sheet_file_test=True
        ).create(
            {
                "statement_filename": "numeric_amounts.xlsx",
                "statement_file": b64encode(buffer.getvalue()),
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.import_file_button()
        statement = self.AccountBankStatement.search(self.statement_domain)
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 3)
        self.assertEqual(
            sorted(statement.line_ids.mapped("amount")), [78.9, 100.0, 1234.56]
        )
        self.assertEqual(
            sorted(statement.line_ids.mapped("ref")), ["26182", "289400", "304102"]
        )

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
