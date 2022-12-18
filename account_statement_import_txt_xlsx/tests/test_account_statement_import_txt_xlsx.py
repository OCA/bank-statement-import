# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from base64 import b64encode
from os import path

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common


class TestAccountBankStatementImportTxtXlsx(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
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
        self.suspense_account = self.env["account.account"].create(
            {
                "code": "987654",
                "name": "Suspense Account",
                "user_type_id": self.env.ref(
                    "account.data_account_type_current_assets"
                ).id,
            }
        )

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
            account_statement_import_txt_xlsx_test=True
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
                account_statement_import_txt_xlsx_test=True
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
            account_statement_import_txt_xlsx_test=True
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
                account_statement_import_txt_xlsx_test=True
            ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 0)

    def test_mapping_import_wizard_xlsx(self):
        with common.Form(self.AccountStatementImportSheetMappingWizard) as form:
            attachment = self.env["ir.attachment"].create(
                {
                    "name": "fixtures/empty_statement_en.xlsx",
                    "datas": self._data_file("fixtures/empty_statement_en.xlsx"),
                }
            )
            form.attachment_ids.add(attachment)
            self.assertEqual(len(form.header), 90)
            self.assertEqual(
                len(
                    self.AccountStatementImportSheetMappingWizard.with_context(
                        header=form.header,
                    ).statement_columns()
                ),
                7,
            )
            form.timestamp_column = "Date"
            form.amount_column = "Amount"
            wizard = form.save()
        wizard.import_mapping()

    def test_mapping_import_wizard_csv(self):
        with common.Form(self.AccountStatementImportSheetMappingWizard) as form:
            attachment = self.env["ir.attachment"].create(
                {
                    "name": "fixtures/empty_statement_en.csv",
                    "datas": self._data_file("fixtures/empty_statement_en.csv"),
                }
            )
            form.attachment_ids.add(attachment)
            self.assertEqual(len(form.header), 90)
            self.assertEqual(
                len(
                    self.AccountStatementImportSheetMappingWizard.with_context(
                        header=form.header,
                    ).statement_columns()
                ),
                7,
            )
            form.timestamp_column = "Date"
            form.amount_column = "Amount"
            wizard = form.save()
        wizard.import_mapping()

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
            account_statement_import_txt_xlsx_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertEqual(line.currency_id, self.currency_usd)
        self.assertEqual(line.amount, 1525.0)
        self.assertEqual(line.foreign_currency_id, self.currency_eur)
        self.assertEqual(line.amount_currency, 1000.0)

    def test_original_currency_no_header(self):
        no_header_statement_map = self.AccountStatementImportSheetMapping.create(
            {
                "name": "Sample Statement",
                "float_thousands_sep": "comma",
                "float_decimal_sep": "dot",
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
            account_statement_import_txt_xlsx_test=True
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
            account_statement_import_txt_xlsx_test=True
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
            account_statement_import_txt_xlsx_test=True
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
            account_statement_import_txt_xlsx_test=True
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
            account_statement_import_txt_xlsx_test=True
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
            account_statement_import_txt_xlsx_test=True
        ).import_file_button()
        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 4)
        self.assertEqual(statement.balance_start, 10.0)
        self.assertEqual(statement.balance_end_real, 1510.0)
        self.assertEqual(statement.balance_end, 1510.0)
