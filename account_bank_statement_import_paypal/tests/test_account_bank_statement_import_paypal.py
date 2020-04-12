# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

from base64 import b64encode
from os import path


class TestAccountBankStatementImportPayPal(common.TransactionCase):
    def setUp(self):
        super(TestAccountBankStatementImportPayPal, self).setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref('base.EUR')
        self.currency_usd = self.env.ref('base.USD')
        self.paypal_statement_map_en = self.env.ref(
            'account_bank_statement_import_paypal.paypal_statement_map_en'
        )
        self.paypal_statement_map_es = self.env.ref(
            'account_bank_statement_import_paypal.paypal_statement_map_es'
        )
        self.paypal_activity_map_en = self.env.ref(
            'account_bank_statement_import_paypal.paypal_activity_map_en'
        )
        self.AccountJournal = self.env['account.journal']
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementImport = self.env[
            'account.bank.statement.import'
        ]
        self.AccountBankStatementImportPayPalMapping = self.env[
            'account.bank.statement.import.paypal.mapping'
        ]
        self.AccountBankStatementImportPayPalMappingWizard = self.env[
            'account.bank.statement.import.paypal.mapping.wizard'
        ]

    def _data_file(self, filename):
        with open(path.join(path.dirname(__file__), filename)) as file:
            return b64encode(file.read().encode('utf-8'))

    def test_import_statement_en_usd(self):
        journal = self.AccountJournal.create({
            'name': 'PayPal',
            'type': 'bank',
            'code': 'PP',
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/statement_en.csv',
            'data_file': self._data_file('fixtures/statement_en.csv'),
            'paypal_mapping_id': self.paypal_statement_map_en.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_paypal_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 18)

    def test_import_statement_en_eur(self):
        journal = self.AccountJournal.create({
            'name': 'PayPal',
            'type': 'bank',
            'code': 'PP',
            'currency_id': self.currency_eur.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/statement_en.csv',
            'data_file': self._data_file('fixtures/statement_en.csv'),
            'paypal_mapping_id': self.paypal_statement_map_en.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_paypal_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 8)

    def test_import_statement_es(self):
        journal = self.AccountJournal.create({
            'name': 'PayPal',
            'type': 'bank',
            'code': 'PP',
            'currency_id': self.currency_eur.id,
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/statement_es.csv',
            'data_file': self._data_file('fixtures/statement_es.csv'),
            'paypal_mapping_id': self.paypal_statement_map_es.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_paypal_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 8)

    def test_import_activity_en(self):
        journal = self.AccountJournal.create({
            'name': 'PayPal',
            'type': 'bank',
            'code': 'PP',
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/activity_en.csv',
            'data_file': self._data_file('fixtures/activity_en.csv'),
            'paypal_mapping_id': self.paypal_activity_map_en.id,
        })
        wizard.with_context({
            'journal_id': journal.id,
            'account_bank_statement_import_paypal_test': True,
        }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 1)
        self.assertEqual(len(statement.line_ids), 71)

    def test_import_empty_activity(self):
        journal = self.AccountJournal.create({
            'name': 'PayPal',
            'type': 'bank',
            'code': 'PP',
        })
        wizard = self.AccountBankStatementImport.with_context({
            'journal_id': journal.id,
        }).create({
            'filename': 'fixtures/empty_activity.csv',
            'data_file': self._data_file('fixtures/empty_activity.csv'),
            'paypal_mapping_id': self.paypal_activity_map_en.id,
        })
        with self.assertRaises(UserError):
            wizard.with_context({
                'journal_id': journal.id,
                'account_bank_statement_import_paypal_test': True,
            }).import_file()
        statement = self.AccountBankStatement.search([
            ('journal_id', '=', journal.id),
        ])
        self.assertEqual(len(statement), 0)

    def test_import_activity_mapping_en(self):
        wizard = self.AccountBankStatementImportPayPalMappingWizard.new({
            'filename': 'fixtures/activity_en.csv',
            'data_file': self._data_file('fixtures/activity_en.csv'),
        })
        wizard._onchange_data_file()
        self.assertEqual(
            len(self.AccountBankStatementImportPayPalMappingWizard
                .with_context(header=wizard.header).statement_columns()),
            22
        )
        wizard.import_mapping()

    def test_import_statement_mapping_en(self):
        wizard = self.AccountBankStatementImportPayPalMappingWizard.new({
            'filename': 'fixtures/statement_en.csv',
            'data_file': self._data_file('fixtures/statement_en.csv'),
        })
        wizard._onchange_data_file()
        self.assertEqual(
            len(self.AccountBankStatementImportPayPalMappingWizard
                .with_context(header=wizard.header).statement_columns()),
            18
        )
        wizard.import_mapping()
