# -*- coding: utf-8 -*-
# Copyright 2017 Onestein (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from mock import patch
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
from ..mt940 import MT940, get_subfields, handle_common_subfields


class TestImport(TransactionCase):
    """Run test to import mt940 import."""
    transactions = [
        {
            'account_number': 'NL46ABNA0499998748',
            'amount': -754.25,
            'ref': '435005714488-ABNO33052620',
            'name': 'test line',
        },
    ]

    def setUp(self):
        super(TestImport, self).setUp()
        bank1 = self.env['res.partner.bank'].create({
            'acc_number': 'NL77INGB0574908765',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.env['account.journal'].create({
            'name': 'Bank Journal - (test1 mt940)',
            'code': 'TBNK1MT940',
            'type': 'bank',
            'bank_account_id': bank1.id,
            'currency_id': self.env.ref('base.EUR').id,
        })
        bank2 = self.env['res.partner.bank'].create({
            'acc_number': 'NL34RABO0142623393',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.env['account.journal'].create({
            'name': 'Bank Journal - (test2 mt940)',
            'code': 'TBNK2MT940',
            'type': 'bank',
            'bank_account_id': bank2.id,
            'currency_id': self.env.ref('base.EUR').id,
        })
        bank3 = self.env['res.partner.bank'].create({
            'acc_number': 'NL05SNSB0908244436',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.env['account.journal'].create({
            'name': 'Bank Journal - (test3 mt940)',
            'code': 'TBNK3MT940',
            'type': 'bank',
            'bank_account_id': bank3.id,
            'currency_id': self.env.ref('base.EUR').id,
        })

        self.data =\
            "/BENM//NAME/Cost/REMI/Period 01-10-2013 t/m 31-12-2013/ISDT/20"
        self.codewords = ['BENM', 'ADDR', 'NAME', 'CNTP', 'ISDT', 'REMI']

    def test_wrong_file_import(self):
        """Test wrong file import."""
        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-wrong-file.940',
        )
        parser = MT940()
        datafile = open(testfile, 'rb').read()
        with self.assertRaises(ValueError):
            parser.parse(datafile, header_lines=1)

    def test_statement_import(self):
        """Test correct creation of single statement ING."""

        def _prepare_statement_lines(statements):
            transact = self.transactions[0]
            for st_vals in statements[2]:
                for line_vals in st_vals['transactions']:
                    line_vals['amount'] = transact['amount']
                    line_vals['name'] = transact['name']
                    line_vals['account_number'] = transact['account_number']
                    line_vals['ref'] = transact['ref']

        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-ing.940',
        )
        parser = MT940()
        datafile = open(testfile, 'rb').read()
        statements = parser.parse(datafile, header_lines=1)

        _prepare_statement_lines(statements)

        path_addon = 'odoo.addons.account_bank_statement_import.'
        path_file = 'account_bank_statement_import.'
        path_class = 'AccountBankStatementImport.'
        method = path_addon + path_file + path_class + '_parse_file'
        with patch(method) as my_mock:
            my_mock.return_value = statements

            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(datafile),
            }).import_file()

            transact = self.transactions[0]
            for statement in self.env['account.bank.statement'].browse(
                    action['context']['statement_ids']):
                for line in statement.line_ids:
                    self.assertTrue(
                        line.bank_account_id.acc_number ==
                        transact['account_number'])
                    self.assertTrue(line.amount == transact['amount'])
                    self.assertTrue(line.date == '2014-02-20')
                    self.assertTrue(line.name == transact['name'])
                    self.assertTrue(line.ref == transact['ref'])

    def test_get_subfields(self):
        """Unit Test function get_subfields()."""

        res = get_subfields(self.data, self.codewords)
        espected_res = {
            'BENM': [''],
            'NAME': ['Cost'],
            'REMI': ['Period 01-10-2013 t', 'm 31-12-2013'],
            'ISDT': ['20'],
        }
        self.assertTrue(res == espected_res)

    def test_handle_common_subfields(self):
        """Unit Test function handle_common_subfields()."""

        subfields = get_subfields(self.data, self.codewords)
        transaction = self.transactions[0]

        handle_common_subfields(transaction, subfields)

    def test_statement_import2(self):
        """Test correct creation of single statement RABO."""

        def _prepare_statement_lines(statements):
            transact = self.transactions[0]
            for st_vals in statements[2]:
                for line_vals in st_vals['transactions']:
                    line_vals['amount'] = transact['amount']
                    line_vals['name'] = transact['name']
                    line_vals['account_number'] = transact['account_number']
                    line_vals['ref'] = transact['ref']

        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-rabo.swi',
        )
        parser = MT940()
        parser.header_regex = '^:940:'  # Start of header
        parser.header_lines = 1  # Number of lines to skip
        datafile = open(testfile, 'rb').read()
        statements = parser.parse(datafile, header_lines=1)

        _prepare_statement_lines(statements)

        path_addon = 'odoo.addons.account_bank_statement_import.'
        path_file = 'account_bank_statement_import.'
        path_class = 'AccountBankStatementImport.'
        method = path_addon + path_file + path_class + '_parse_file'
        with patch(method) as my_mock:
            my_mock.return_value = statements

            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(datafile),
            }).import_file()
            # The file contains 4 statements, but only 2 with transactions
            self.assertTrue(len(action['context']['statement_ids']) == 2)
            transact = self.transactions[0]
            for statement in self.env['account.bank.statement'].browse(
                    action['context']['statement_ids']):
                for line in statement.line_ids:
                    self.assertTrue(
                        line.bank_account_id.acc_number ==
                        transact['account_number'])
                    self.assertTrue(line.amount == transact['amount'])
                    self.assertTrue(line.date)
                    self.assertTrue(line.name == transact['name'])
                    self.assertTrue(line.ref == transact['ref'])

    def test_statement_import3(self):
        """Test correct creation of multiple statements SNS."""

        def _prepare_statement_lines(statements):
            transact = self.transactions[0]
            for st_vals in statements[2]:
                for line_vals in st_vals['transactions']:
                    line_vals['amount'] = transact['amount']
                    line_vals['name'] = transact['name']
                    line_vals['account_number'] = transact['account_number']
                    line_vals['ref'] = transact['ref']

        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-sns.940',
        )
        parser = MT940()
        datafile = open(testfile, 'rb').read()
        statements = parser.parse(datafile, header_lines=1)

        _prepare_statement_lines(statements)

        path_addon = 'odoo.addons.account_bank_statement_import.'
        path_file = 'account_bank_statement_import.'
        path_class = 'AccountBankStatementImport.'
        method = path_addon + path_file + path_class + '_parse_file'
        with patch(method) as my_mock:
            my_mock.return_value = statements

            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(datafile),
            }).import_file()
            self.assertTrue(len(action['context']['statement_ids']) == 3)
            transact = self.transactions[-1]
            for statement in self.env['account.bank.statement'].browse(
                    action['context']['statement_ids'][-1]):
                for line in statement.line_ids:
                    self.assertTrue(
                        line.bank_account_id.acc_number ==
                        transact['account_number'])
                    self.assertTrue(line.amount == transact['amount'])
                    self.assertTrue(line.date == statement.date)
                    self.assertTrue(line.name == transact['name'])
                    self.assertTrue(line.ref == transact['ref'])
