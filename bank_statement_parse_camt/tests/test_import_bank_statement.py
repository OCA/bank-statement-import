# -*- coding: utf-8 -*-
"""Run test to import camt.053 import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    All other contributions are (C) by their respective contributors
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
from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


class TestStatementFile(TransactionCase):
    """Run test to import camt.053 import."""

    def test_statement_import(self):
        """Test correct creation of single statement."""
        import_model = self.registry('account.bank.statement.import')
        statement_model = self.registry('account.bank.statement')
        cr, uid = self.cr, self.uid
        statement_path = get_module_resource(
            'bank_statement_parse_camt',
            'test_files',
            'test-camt053.xml'
        )
        statement_file = open(
            statement_path, 'rb').read().encode('base64')
        bank_statement_id = import_model.create(
            cr, uid,
            dict(
                data_file=statement_file,
            )
        )
        import_model.import_file(cr, uid, [bank_statement_id])
        ids = statement_model.search(
            cr, uid, [('name', '=', '1234Test/1')])
        self.assertTrue(ids, 'Statement not found after parse.')
        statement_id = ids[0]
        statement_obj = statement_model.browse(
            cr, uid, statement_id)
        self.assertTrue(
            abs(statement_obj.balance_start - 15568.27) < 0.00001,
            'Start balance %f not equal to 15568.27' %
            statement_obj.balance_start
        )
        self.assertTrue(
            abs(statement_obj.balance_end_real - 15121.12) < 0.00001,
            'Real end balance %f not equal to 15121.12' %
            statement_obj.balance_end_real
        )
