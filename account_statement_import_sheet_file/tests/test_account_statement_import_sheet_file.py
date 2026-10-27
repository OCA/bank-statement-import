# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from datetime import timedelta
from decimal import Decimal
from os import path
from unittest.mock import Mock, patch

import xlrd

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common, tagged
from odoo.tools import float_round

from ..models.account_statement_import_sheet_parser import _OpenpyxlSheet


@tagged("post_install", "-at_install")
class TestAccountStatementImportSheetFile(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if not cls.env.company.chart_template_id:
            # Load a CoA if there's none in current company
            coa = cls.env.ref("l10n_generic_coa.configurable_chart_template", False)
            if not coa:
                # Load the first available CoA
                coa = cls.env["account.chart.template"].search(
                    [("visible", "=", True)], limit=1
                )
            coa.try_loading(company=cls.env.company, install_demo=False)
        cls.now = fields.Datetime.now()
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_usd = cls.env.ref("base.USD")
        cls.currency_usd.active = True
        # Make sure the currency of the company is USD, as this not always happens
        # To be removed in V17: https://github.com/odoo/odoo/pull/107113
        cls.company = cls.env.company
        cls.env.cr.execute(
            "UPDATE res_company SET currency_id = %s WHERE id = %s",
            (cls.env.ref("base.USD").id, cls.company.id),
        )
        # Activate EUR for unit test, by default is not active
        cls.currency_eur.active = True
        cls.sample_statement_map = cls.env.ref(
            "account_statement_import_sheet_file.sample_statement_map"
        )
        cls.AccountJournal = cls.env["account.journal"]
        cls.AccountBankStatement = cls.env["account.bank.statement"]
        cls.AccountStatementImport = cls.env["account.statement.import"]
        cls.AccountStatementImportSheetMapping = cls.env[
            "account.statement.import.sheet.mapping"
        ]
        cls.AccountStatementImportWizard = cls.env["account.statement.import"]
        cls.suspense_account = cls.env["account.account"].create(
            {
                "code": "987654",
                "name": "Suspense Account",
                "account_type": "asset_current",
            }
        )
        cls.parser = cls.env["account.statement.import.sheet.parser"]
        # Mock the mapping object to return predefined separators
        cls.mock_mapping_comma_dot = Mock()
        cls.mock_mapping_comma_dot._get_float_separators.return_value = (",", ".")
        cls.mock_mapping_dot_comma = Mock()
        cls.mock_mapping_dot_comma._get_float_separators.return_value = (".", ",")

    def _data_file(self, filename, encoding=None):
        mode = "rt" if encoding else "rb"
        with open(path.join(path.dirname(__file__), filename), mode) as file:
            data = file.read()
            if encoding:
                data = data.encode(encoding)
            return b64encode(data)

    def test_import_csv_file(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/sample_statement_en.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/sample_statement_en.csv",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)

    def test_import_empty_csv_file(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/empty_statement_en.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/empty_statement_en.csv",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.with_context(
                account_statement_import_sheet_file_test=True
            ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 0)

    def test_import_xlsx_file(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/sample_statement_en.xlsx")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/sample_statement_en.xlsx",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)

    def test_import_empty_xlsx_file(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/empty_statement_en.xlsx")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/empty_statement_en.xlsx",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.with_context(
                account_statement_import_sheet_file_test=True
            ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 0)

    def test_original_currency(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/original_currency.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/original_currency.csv",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertEqual(line.currency_id, self.currency_usd)
        self.assertEqual(line.amount, 1525.0)
        self.assertEqual(line.foreign_currency_id, self.currency_eur)
        line_amount_currency = float_round(line.amount_currency, precision_digits=1)
        self.assertEqual(line_amount_currency, 1000.0)

    def test_original_currency_no_header(self):
        no_header_statement_map = self.AccountStatementImportSheetMapping.create(
            {
                "name": "Sample Statement",
                "float_thousands_sep": "comma",
                "float_decimal_sep": "dot",
                "header_lines_skip_count": 0,
                "delimiter": "comma",
                "quotechar": '"',
                "timestamp_format": "%m/%d/%Y",
                "no_header": True,
                "timestamp_column": "0",
                "amount_column": "3",
                "original_currency_column": "2",
                "original_amount_column": "4",
                "description_column": "1,7",
                "partner_name_column": "5",
                "bank_account_column": "6",
            }
        )
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/original_currency_no_header.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/original_currency.csv",
                "statement_file": data,
                "sheet_mapping_id": no_header_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertEqual(line.currency_id, self.currency_usd)
        self.assertEqual(line.foreign_currency_id, self.currency_eur)
        self.assertEqual(line.amount_currency, 1000.0)
        self.assertEqual(line.payment_ref, "Your payment INV0001")

    def test_original_currency_empty(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/original_currency_empty.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/original_currency_empty.csv",
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertFalse(line.foreign_currency_id)
        self.assertEqual(line.amount_currency, 0.0)

    def test_multi_currency(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        statement_map = self.sample_statement_map.copy(
            {
                "currency_column": "Currency",
                "original_currency_column": None,
                "original_amount_column": None,
            }
        )
        data = self._data_file("fixtures/multi_currency.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/multi_currency.csv",
                "statement_file": data,
                "sheet_mapping_id": statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertFalse(line.foreign_currency_id)
        self.assertEqual(line.amount, -33.5)

    def test_balance(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        statement_map = self.sample_statement_map.copy(
            {
                "balance_column": "Balance",
                "original_currency_column": None,
                "original_amount_column": None,
            }
        )
        data = self._data_file("fixtures/balance.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/balance.csv",
                "statement_file": data,
                "sheet_mapping_id": statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_start, 10.0)
        self.assertEqual(statement.balance_end_real, 1510.0)
        self.assertEqual(statement.balance_end, 1510.0)

    def test_debit_credit(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        statement_map = self.sample_statement_map.copy(
            {
                "balance_column": "Balance",
                "original_currency_column": None,
                "original_amount_column": None,
                "debit_credit_column": "D/C",
                "debit_value": "D",
                "credit_value": "C",
            }
        )
        data = self._data_file("fixtures/debit_credit.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/debit_credit.csv",
                "statement_file": data,
                "sheet_mapping_id": statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_start, 10.0)
        self.assertEqual(statement.balance_end_real, 1510.0)
        self.assertEqual(statement.balance_end, 1510.0)

    def test_debit_credit_amount(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        statement_map = self.sample_statement_map.copy(
            {
                "amount_type": "distinct_credit_debit",
                "amount_debit_column": "Debit",
                "amount_credit_column": "Credit",
                "balance_column": "Balance",
                "amount_column": None,
                "original_currency_column": None,
                "original_amount_column": None,
            }
        )
        data = self._data_file("fixtures/debit_credit_amount.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/debit_credit_amount.csv",
                "statement_file": data,
                "sheet_mapping_id": statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 4)
        self.assertEqual(statement.balance_start, 10.0)
        self.assertEqual(statement.balance_end_real, 1510.0)
        self.assertEqual(statement.balance_end, 1510.0)

    def test_metadata_separated_debit_credit_csv(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        statement_map = self.sample_statement_map.copy(
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
        data = self._data_file("fixtures/meta_data_separated_credit_debit.csv", "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/meta_data_separated_credit_debit.csv",
                "statement_file": data,
                "sheet_mapping_id": statement_map.id,
            }
        )
        wizard.with_context(
            journal_id=journal.id,
            account_bank_statement_import_txt_xlsx_test=True,
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 4)
        line1 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 1")
        line4 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 4")
        self.assertEqual(line1.amount, 50)
        self.assertEqual(line4.amount, -1300)

    def test_metadata_separated_debit_credit_xlsx(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        statement_map = self.sample_statement_map.copy(
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
        data = self._data_file("fixtures/meta_data_separated_credit_debit.xlsx")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/meta_data_separated_credit_debit.xlsx",
                "statement_file": data,
                "sheet_mapping_id": statement_map.id,
            }
        )
        wizard.with_context(
            journal_id=journal.id,
            account_bank_statement_import_txt_xlsx_test=True,
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 4)
        line1 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 1")
        line4 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 4")
        self.assertEqual(line1.amount, 50)
        self.assertEqual(line4.amount, -1300)

    def test_amount_inverse_sign(self):
        self.sample_statement_map.amount_inverse_sign = True
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        filename = "fixtures/sample_statement_credit_card_inverse_sign_en.csv"
        data = self._data_file(filename, "utf-8")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": filename,
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        line1 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 1")
        self.assertEqual(line1.amount, -33.50)
        line2 = statement.line_ids.filtered(lambda x: x.payment_ref == "LABEL 2")
        self.assertEqual(line2.amount, 1525.00)
        self.assertEqual(line2.amount_currency, 1000.00)

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
        journal = self.AccountJournal.create(
            {
                "name": "Bank 2",
                "type": "bank",
                "code": "BAN2",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        data = self._data_file("fixtures/sample_statement_en_empty_values.xlsx")
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": "fixtures/sample_statement_en_empty_values.xlsx",
                "statement_file": data,
                "sheet_mapping_id": sample_statement_map_empty_values.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 3)

    def test_parse_decimal(self):
        # Define a series of test cases
        test_cases = [
            (
                "1,234.56",
                1234.56,
                self.mock_mapping_comma_dot,
            ),  # standard case with thousands separator
            (
                "1,234,567.89",
                1234567.89,
                self.mock_mapping_comma_dot,
            ),  # multiple thousands separators
            (
                "-1,234.56",
                -1234.56,
                self.mock_mapping_comma_dot,
            ),  # negative value
            (
                "$1,234.56",
                1234.56,
                self.mock_mapping_comma_dot,
            ),  # prefixed with currency symbol
            (
                "1,234.56 USD",
                1234.56,
                self.mock_mapping_comma_dot,
            ),  # suffixed with currency code
            (
                "   1,234.56   ",
                1234.56,
                self.mock_mapping_comma_dot,
            ),  # leading and trailing spaces
            (
                "not a number",
                0,
                self.mock_mapping_comma_dot,
            ),  # non-numeric input
            (" ", 0, self.mock_mapping_comma_dot),  # empty string
            ("", 0, self.mock_mapping_comma_dot),  # empty space
            ("USD", 0, self.mock_mapping_comma_dot),  # empty dolar
            (
                "12,34.56",
                1234.56,
                self.mock_mapping_comma_dot,
            ),  # unusual thousand separator placement
            (
                "1234,567.89",
                1234567.89,
                self.mock_mapping_comma_dot,
            ),  # missing one separator
            (
                "1234.567,89",
                1234567.89,
                self.mock_mapping_dot_comma,
            ),  # inverted separators
        ]

        for value, expected, mock_mapping in test_cases:
            with self.subTest(value=value):
                result = self.parser._parse_decimal(value, mock_mapping)
                self.assertEqual(result, expected, f"Failed for value: {value}")

    def test_decimal_and_float_inputs(self):
        # Test direct Decimal and float inputs
        self.assertEqual(
            self.parser._parse_decimal(-1234.56, self.mock_mapping_comma_dot),
            -1234.56,
        )
        self.assertEqual(
            self.parser._parse_decimal(1234.56, self.mock_mapping_comma_dot),
            1234.56,
        )
        self.assertEqual(
            self.parser._parse_decimal(
                Decimal("-1234.56"), self.mock_mapping_comma_dot
            ),
            -1234.56,
        )
        self.assertEqual(
            self.parser._parse_decimal(Decimal("1234.56"), self.mock_mapping_comma_dot),
            1234.56,
        )

    def test_offsets(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        file_name = "fixtures/sample_statement_offsets.xlsx"
        data = self._data_file(file_name)
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": file_name,
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.with_context(
                account_statement_import_txt_xlsx_test=True
            ).import_file_button()
        statement_map_offsets = self.sample_statement_map.copy(
            {
                "offset_column": 1,
                "header_lines_skip_count": 3,
            }
        )
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": file_name,
                "statement_file": data,
                "sheet_mapping_id": statement_map_offsets.id,
            }
        )
        wizard.with_context(
            account_statement_import_txt_xlsx_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_start, 0.0)
        self.assertEqual(statement.balance_end_real, 1491.5)
        self.assertEqual(statement.balance_end, 1491.5)

    def test_skip_empty_lines(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )
        file_name = "fixtures/empty_lines_statement.csv"
        data = self._data_file(file_name, "utf-8")

        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": file_name,
                "statement_file": data,
                "sheet_mapping_id": self.sample_statement_map.id,
            }
        )
        with self.assertRaises(UserError):
            wizard.with_context(
                account_statement_import_txt_xlsx_test=True
            ).import_file_button()
        statement_map_empty_line = self.sample_statement_map.copy(
            {
                "skip_empty_lines": True,
            }
        )
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": file_name,
                "statement_file": data,
                "sheet_mapping_id": statement_map_empty_line.id,
            }
        )
        wizard.with_context(
            account_statement_import_txt_xlsx_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 3)
        self.assertEqual(statement.balance_start, 0.0)
        self.assertEqual(statement.balance_end_real, 2291.5)
        self.assertEqual(statement.balance_end, 2291.5)

    XLRD_OPEN_WORKBOOK = (
        "odoo.addons.account_statement_import_sheet_file.models."
        "account_statement_import_sheet_parser.xlrd.open_workbook"
    )

    def _xlrd2_xlsx_error(self):
        return patch(
            self.XLRD_OPEN_WORKBOOK,
            side_effect=xlrd.XLRDError("Excel xlsx file; not supported"),
        )

    def _create_journal(self, code="BANK"):
        return self.AccountJournal.create(
            {
                "name": "Bank %s" % code,
                "type": "bank",
                "code": code,
                "currency_id": self.currency_usd.id,
                "suspense_account_id": self.suspense_account.id,
            }
        )

    def _import_fixture(self, filename, mapping, journal=None):
        journal = journal or self._create_journal()
        wizard = self.AccountStatementImport.with_context(journal_id=journal.id).create(
            {
                "statement_filename": filename,
                "statement_file": self._data_file(filename),
                "sheet_mapping_id": mapping.id,
            }
        )
        wizard.with_context(
            account_statement_import_sheet_file_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1, "Expected exactly one statement")
        return statement

    def _lines_signature(self, statement):
        return sorted(
            (
                line.amount,
                str(line.date),
                line.payment_ref,
                # The journal id is part of the stored unique id: strip it
                (line.unique_import_id or "").replace(
                    "%s-" % line.journal_id.id, "", 1
                ),
            )
            for line in statement.line_ids
        )

    def _assert_sample_lines(self, statement):
        self.assertEqual(len(statement.line_ids), 2)
        lines = statement.line_ids.sorted("amount")
        self.assertEqual(lines[0].amount, -33.5)
        self.assertEqual(lines[1].amount, 1525.0)
        self.assertEqual(
            lines.mapped("date"),
            [fields.Date.to_date("2018-12-15")] * 2,
        )
        self.assertEqual(
            lines.mapped("payment_ref"),
            [
                "Your best supplier on 12/15/2018",
                "Your payment on 12/15/2018",
            ],
        )

    def _empty_values_map(self):
        return self.AccountStatementImportSheetMapping.create(
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

    def test_01_xlsx_reader_xlrd(self):
        statement = self._import_fixture(
            "fixtures/sample_statement_en.xlsx", self.sample_statement_map
        )
        self._assert_sample_lines(statement)

    def test_02_xlsx_reader_openpyxl_fallback(self):
        filename = "fixtures/sample_statement_en.xlsx"
        journal_xlrd = self._create_journal("BANK")
        journal_fallback = self._create_journal("BNK2")
        expected = self._lines_signature(
            self._import_fixture(filename, self.sample_statement_map, journal_xlrd)
        )
        # Free the unique ids so the second import is not filtered as duplicate
        self.AccountBankStatement.search(
            [("journal_id", "=", journal_xlrd.id)]
        ).line_ids.unlink()
        with self._xlrd2_xlsx_error():
            statement = self._import_fixture(
                filename, self.sample_statement_map, journal_fallback
            )
        self._assert_sample_lines(statement)
        self.assertEqual(self._lines_signature(statement), expected)

    def test_03_xlsx_fallback_footer_trailing_rows(self):
        mapping = self._empty_values_map()
        for code_xlrd, code_fallback, filename in (
            ("BNK3", "BNK4", "fixtures/sample_statement_en_trailing_rows.xlsx"),
            ("BNK5", "BNK6", "fixtures/sample_statement_en_empty_values.xlsx"),
        ):
            expected = self._import_fixture(
                filename, mapping, self._create_journal(code_xlrd)
            )
            self.assertEqual(len(expected.line_ids), 3)
            signature = self._lines_signature(expected)
            expected.line_ids.unlink()
            with self._xlrd2_xlsx_error():
                statement = self._import_fixture(
                    filename, mapping, self._create_journal(code_fallback)
                )
            self.assertEqual(self._lines_signature(statement), signature)

    def test_04_xls_binary_import(self):
        statement = self._import_fixture(
            "fixtures/sample_statement_en.xls", self.sample_statement_map
        )
        self._assert_sample_lines(statement)

    def test_05_xlsx_header_skip_zero(self):
        mapping = self.sample_statement_map.copy({"header_lines_skip_count": 0})
        statement = self._import_fixture(
            "fixtures/sample_statement_header_skip_zero.xlsx", mapping
        )
        self._assert_sample_lines(statement)

    def test_06_markup_disguised_xls_error(self):
        with self.assertRaisesRegex(UserError, "web page"):
            self._import_fixture(
                "fixtures/markup_statement.xls", self.sample_statement_map
            )

    def test_07_corrupt_xlsx_error(self):
        with self._xlrd2_xlsx_error(), self.assertRaisesRegex(
            UserError, "could not be read as.*XLSX"
        ):
            self._import_fixture(
                "fixtures/corrupt_statement.xlsx", self.sample_statement_map
            )
        with self.assertRaisesRegex(UserError, "could not be read as.*XLSX"):
            self._import_fixture(
                "fixtures/corrupt_statement.xlsx",
                self.sample_statement_map,
                self._create_journal("BNK2"),
            )

    def test_08_csv_starting_with_angle_bracket(self):
        mapping = self.sample_statement_map.copy({"timestamp_column": "<DTPOSTED>"})
        statement = self._import_fixture(
            "fixtures/angle_bracket_statement.csv", mapping
        )
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(
            sorted(statement.line_ids.mapped("amount")),
            [-33.5, 1525.0],
        )
        self.assertEqual(
            sorted(str(d) for d in statement.line_ids.mapped("date")),
            ["2018-12-15", "2018-12-16"],
        )

    def test_09_truncated_sheet_xlsx_error(self):
        with self._xlrd2_xlsx_error(), self.assertRaisesRegex(
            UserError, "could not be read as.*XLSX"
        ):
            self._import_fixture(
                "fixtures/truncated_sheet_statement.xlsx", self.sample_statement_map
            )
        with self.assertRaisesRegex(UserError, "could not be read as.*XLSX"):
            self._import_fixture(
                "fixtures/truncated_sheet_statement.xlsx",
                self.sample_statement_map,
                self._create_journal("BNK2"),
            )

    def test_10_corrupt_xls_error(self):
        with self.assertRaisesRegex(UserError, "could not be read as XLS:"):
            self._import_fixture(
                "fixtures/corrupt_statement.xls", self.sample_statement_map
            )

    def test_11_openpyxl_duration_as_days(self):
        self.assertEqual(
            _OpenpyxlSheet._normalize(timedelta(hours=1, minutes=30)), 0.0625
        )
