# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

from base64 import b64encode
from os import path


class TestAccountBankStatementImportTxtXlsx(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref('base.EUR')
        self.currency_usd = self.env.ref('base.USD')
        self.sample_statement_map = self.env.ref(
            'account_bank_statement_import_txt_xlsx.sample_statement_map'
        )
        self.AccountJournal = self.env['account.journal']
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementImport = self.env[
            'account.bank.statement.import'
        ]
        self.AccountBankStatementImportSheetMapping = self.env[
            'account.bank.statement.import.sheet.mapping'
        ]
        self.AccountBankStatementImportSheetMappingWizard = self.env[
            'account.bank.statement.import.sheet.mapping.wizard'
        ]

    def _data_file(self, filename, encoding=None):
        mode = 'rt' if encoding else 'rb'
        with open(path.join(path.dirname(__file__), filename), mode) as file:
            data = file.read()
            if encoding:
                data = data.encode(encoding)
            return b64encode(data)

    def test_import_csv_file(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/sample_statement_en.csv',
            'data_file': self._data_file(
                'fixtures/sample_statement_en.csv',
                'utf-8'
            ),
            'sheet_mapping_id': self.sample_statement_map.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_txt_xlsx_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)

    def test_import_empty_csv_file(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/empty_statement_en.csv',
            'data_file': self._data_file(
                'fixtures/empty_statement_en.csv',
                'utf-8'
            ),
            'sheet_mapping_id': self.sample_statement_map.id,
        })
        with self.assertRaises(UserError):
            wizard.with_context({
                'journal_id': journal.id,
                'account_bank_statement_import_txt_xlsx_test': True,
            }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 0)

    def test_import_xlsx_file(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/sample_statement_en.xlsx',
            'data_file': self._data_file('fixtures/sample_statement_en.xlsx'),
            'sheet_mapping_id': self.sample_statement_map.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_txt_xlsx_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)

    def test_import_empty_xlsx_file(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/empty_statement_en.xlsx',
            'data_file': self._data_file('fixtures/empty_statement_en.xlsx'),
            'sheet_mapping_id': self.sample_statement_map.id,
        })
        with self.assertRaises(UserError):
            wizard.with_context({
                'journal_id': journal.id,
                'account_bank_statement_import_txt_xlsx_test': True,
            }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 0)

    def test_mapping_import_wizard_xlsx(self):
        with common.Form(
                self.AccountBankStatementImportSheetMappingWizard) as form:
            form.filename = 'fixtures/empty_statement_en.xlsx'
            form.data_file = self._data_file(
                'fixtures/empty_statement_en.xlsx'
            )
            self.assertEqual(len(form.header), 90)
            self.assertEqual(
                len(
                    self.AccountBankStatementImportSheetMappingWizard
                        .with_context(
                            header=form.header,
                        ).statement_columns()
                ),
                7
            )
            form.timestamp_column = 'Date'
            form.amount_column = 'Amount'
            wizard = form.save()
        wizard.import_mapping()

    def test_mapping_import_wizard_csv(self):
        with common.Form(
                self.AccountBankStatementImportSheetMappingWizard) as form:
            form.filename = 'fixtures/empty_statement_en.csv'
            form.data_file = self._data_file(
                'fixtures/empty_statement_en.csv'
            )
            self.assertEqual(len(form.header), 90)
            self.assertEqual(
                len(
                    self.AccountBankStatementImportSheetMappingWizard
                        .with_context(
                            header=form.header,
                        ).statement_columns()
                ),
                7
            )
            form.timestamp_column = 'Date'
            form.amount_column = 'Amount'
            wizard = form.save()
        wizard.import_mapping()

    def test_original_currency(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/original_currency.csv',
            'data_file': self._data_file(
                'fixtures/original_currency.csv',
                'utf-8'
            ),
            'sheet_mapping_id': self.sample_statement_map.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_txt_xlsx_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertEqual(line.currency_id, self.currency_eur)
        self.assertEqual(line.amount_currency, 1000.0)

    def test_multi_currency(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        statement_map = self.sample_statement_map.copy({
            'currency_column': 'Currency',
            'original_currency_column': None,
            'original_amount_column': None,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/multi_currency.csv',
            'data_file': self._data_file(
                'fixtures/multi_currency.csv',
                'utf-8'
            ),
            'sheet_mapping_id': statement_map.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_txt_xlsx_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

        line = statement.line_ids
        self.assertFalse(line.currency_id)
        self.assertEqual(line.amount, -33.5)

    def test_balance(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        statement_map = self.sample_statement_map.copy({
            'balance_column': 'Balance',
            'original_currency_column': None,
            'original_amount_column': None,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/balance.csv',
            'data_file': self._data_file(
                'fixtures/balance.csv',
                'utf-8'
            ),
            'sheet_mapping_id': statement_map.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_txt_xlsx_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_start, 10.0)
        self.assertEqual(statement.balance_end_real, 1510.0)
        self.assertEqual(statement.balance_end, 1510.0)

    def test_debit_credit(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        statement_map = self.sample_statement_map.copy({
            'balance_column': 'Balance',
            'original_currency_column': None,
            'original_amount_column': None,
            'debit_credit_column': 'D/C',
            'debit_value': 'D',
            'credit_value': 'C',
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/debit_credit.csv',
            'data_file': self._data_file(
                'fixtures/debit_credit.csv',
                'utf-8'
            ),
            'sheet_mapping_id': statement_map.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_txt_xlsx_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(statement.balance_start, 10.0)
        self.assertEqual(statement.balance_end_real, 1510.0)
        self.assertEqual(statement.balance_end, 1510.0)
