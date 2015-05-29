# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
from openerp import models
from openerp.tests.common import TransactionCase


class HelloWorldParser(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
        return 'EUR', 'BE1234567890', [{
            'name': '000000123',
            'date': '2013-06-26',
            'transactions': [{
                'name': 'KBC-INVESTERINGSKREDIET 787-5562831-01',
                'date': '2013-06-26',
                'amount': 42,
                'unique_import_id': 'hello',
            }],
        }]


class TestSaveFile(TransactionCase):
    def test_SaveFile(self):
        HelloWorldParser._build_model(self.registry, self.cr)
        testmodel = self.env['account.bank.statement.import']
        testmodel._prepare_setup()
        testmodel._setup_base(False)
        testmodel._setup_fields()
        testmodel._setup_complete()
        testmodel._auto_init()
        action = self.env['account.bank.statement.import']\
            .with_context(
                journal_id=self.env['account.journal']
                .search([('currency.name', '=', 'EUR')]).ids[0])\
            .create({'data_file': base64.b64encode('hello world')})\
            .import_file()
        for statement in self.env['account.bank.statement'].browse(
                action['context']['statement_ids']):
            self.assertEqual(
                base64.b64decode(statement.import_file.datas),
                'hello world')
