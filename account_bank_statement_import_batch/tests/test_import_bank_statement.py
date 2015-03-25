# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of account_bank_statement_import_coda,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     account_bank_statement_import_coda is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     account_bank_statement_import_coda is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with account_bank_statement_import_coda.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import mock
from mock import call

from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestImportBatch(TransactionCase):
    """Tests for batch import of bank statement files
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestImportBatch, self).setUp()
        self.statement_import_model = self.env[
            'account.bank.statement.import']
        self.bank_statement_model = self.env['account.bank.statement']
        zip_file_path = get_module_resource(
            'account_bank_statement_import_batch',
            'tests',
            'test.zip')
        self.zip_file = open(zip_file_path, 'rb').read().encode('base64')
        txt_file_path = get_module_resource(
            'account_bank_statement_import_batch',
            'tests',
            'test.txt')
        self.txt_file = open(txt_file_path, 'rb').read().encode('base64')

    def test_zip_file_import(self):
        with mock.patch('openerp.addons.'
                        'account_bank_statement_import.'
                        'account_bank_statement_import.'
                        'account_bank_statement_import.'
                        '_import_file') as mocked:
            mocked.side_effect = [([1], [{'message': '1',
                                          'type': 'warning'}]),
                                  ([3], [{'message': '2',
                                          'type': 'error'}])]
            bank_statement_import = self.statement_import_model.create(
                {'data_file': self.zip_file})
            res = bank_statement_import.import_file()
            self.assertEqual(
                2, mocked.call_count,
                'import_file should be called 2 times : '
                '1 time for each file in the archive')
            mocked.assert_has_calls([call('test1\n'), call('test2\n')])
            self.assertDictEqual({'default_errors': '* 2',
                                  'default_warnings': '* 1'},
                                 res.get('context'))

    def test_text_file_import(self):
        with mock.patch('openerp.addons.'
                        'account_bank_statement_import.'
                        'account_bank_statement_import.'
                        'account_bank_statement_import.'
                        '_import_file') as mocked:
            mocked.side_effect = [([1], [])]
            bank_statement_import = self.statement_import_model.create(
                {'data_file': self.txt_file})
            res = bank_statement_import.import_file()
            self.assertEqual(
                1, mocked.call_count,
                'import_file should be called 1 times (not an archive)')
            mocked.assert_has_calls([call('test1\n')])
            self.assertDictEqual({'statement_ids': [1],
                                  'notifications': []}, res.get('context'))
