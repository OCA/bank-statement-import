# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.tests import common

from base64 import b64encode
from unittest import mock

_parse_file_method = (
    'odoo.addons.account_bank_statement_import'
    '.account_bank_statement_import.AccountBankStatementImport._parse_file'
)


class TestAccountBankAccountStatementImportSplit(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_usd = self.env.ref('base.USD')
        self.empty_data_file = b64encode(
            'TestAccountBankAccountStatementImportSplit'.encode('utf-8')
        )
        self.AccountJournal = self.env['account.journal']
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementImport = self.env[
            'account.bank.statement.import'
        ]

    def test_default_import_mode(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'file.ext',
            'data_file': self.empty_data_file,
        })
        data = (
            journal.currency_id.name,
            journal.bank_account_id.acc_number,
            [{
                'name': 'STATEMENT',
                'date': '2019-01-01',
                'balance_start': 0.0,
                'balance_end_real': 100.0,
                'transactions': [{
                    'name': 'TRANSACTION',
                    'amount': '100.0',
                    'date': '2019-01-01',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID',
                }],
            }],
        )
        with mock.patch(_parse_file_method, return_value=data):
            wizard.with_context({
                'journal_id': journal.id,
            }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

    def test_single_import_mode(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'file.ext',
            'data_file': self.empty_data_file,
            'import_mode': 'single',
        })
        data = (
            journal.currency_id.name,
            journal.bank_account_id.acc_number,
            [{
                'name': 'STATEMENT',
                'date': '2019-01-01',
                'balance_start': 0.0,
                'balance_end_real': 100.0,
                'transactions': [{
                    'name': 'TRANSACTION',
                    'amount': '100.0',
                    'date': '2019-01-01',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID',
                }],
            }],
        )
        with mock.patch(_parse_file_method, return_value=data):
            wizard.with_context({
                'journal_id': journal.id,
            }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 1)

    def test_daily_import_mode(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'file.ext',
            'data_file': self.empty_data_file,
            'import_mode': 'daily',
        })
        data = (
            journal.currency_id.name,
            journal.bank_account_id.acc_number,
            [{
                'name': 'STATEMENT',
                'date': '2019-01-01',
                'balance_start': 0.0,
                'balance_end_real': 100.0,
                'transactions': [{
                    'name': 'TRANSACTION-1',
                    'amount': '50.0',
                    'date': '2019-01-01',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID-1',
                }, {
                    'name': 'TRANSACTION-2',
                    'amount': '50.0',
                    'date': '2019-01-03',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID-2',
                }],
            }],
        )
        with mock.patch(_parse_file_method, return_value=data):
            wizard.with_context({
                'journal_id': journal.id,
            }).import_file()
        statements = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ]).sorted(key=lambda statement: statement.date)
        self.assertEqual(len(statements), 2)
        self.assertEqual(len(statements[0].line_ids), 1)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 50.0)
        self.assertEqual(len(statements[1].line_ids), 1)
        self.assertEqual(statements[1].balance_start, 50.0)
        self.assertEqual(statements[1].balance_end_real, 100.0)

    def test_weekly_import_mode(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'file.ext',
            'data_file': self.empty_data_file,
            'import_mode': 'weekly',
        })
        data = (
            journal.currency_id.name,
            journal.bank_account_id.acc_number,
            [{
                'name': 'STATEMENT',
                'date': '2019-01-01',
                'balance_start': 0.0,
                'balance_end_real': 100.0,
                'transactions': [{
                    'name': 'TRANSACTION-1',
                    'amount': '50.0',
                    'date': '2019-01-01',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID-1',
                }, {
                    'name': 'TRANSACTION-2',
                    'amount': '50.0',
                    'date': '2019-01-15',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID-2',
                }],
            }],
        )
        with mock.patch(_parse_file_method, return_value=data):
            wizard.with_context({
                'journal_id': journal.id,
            }).import_file()
        statements = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ]).sorted(key=lambda statement: statement.date)
        self.assertEqual(len(statements), 2)
        self.assertEqual(len(statements[0].line_ids), 1)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 50.0)
        self.assertEqual(len(statements[1].line_ids), 1)
        self.assertEqual(statements[1].balance_start, 50.0)
        self.assertEqual(statements[1].balance_end_real, 100.0)

    def test_monthly_import_mode(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_usd.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'file.ext',
            'data_file': self.empty_data_file,
            'import_mode': 'monthly',
        })
        data = (
            journal.currency_id.name,
            journal.bank_account_id.acc_number,
            [{
                'name': 'STATEMENT',
                'date': '2019-01-01',
                'balance_start': 0.0,
                'balance_end_real': 100.0,
                'transactions': [{
                    'name': 'TRANSACTION-1',
                    'amount': '50.0',
                    'date': '2019-01-01',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID-1',
                }, {
                    'name': 'TRANSACTION-2',
                    'amount': '50.0',
                    'date': '2019-03-01',
                    'note': 'NOTE',
                    'unique_import_id': 'TRANSACTION-ID-2',
                }],
            }],
        )
        with mock.patch(_parse_file_method, return_value=data):
            wizard.with_context({
                'journal_id': journal.id,
            }).import_file()
        statements = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ]).sorted(key=lambda statement: statement.date)
        self.assertEqual(len(statements), 2)
        self.assertEqual(len(statements[0].line_ids), 1)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 50.0)
        self.assertEqual(len(statements[1].line_ids), 1)
        self.assertEqual(statements[1].balance_start, 50.0)
        self.assertEqual(statements[1].balance_end_real, 100.0)
