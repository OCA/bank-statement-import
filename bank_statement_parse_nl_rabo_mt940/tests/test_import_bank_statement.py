# -*- coding: utf-8 -*-
"""Run test to import MT940 IBAN RABO import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    All other contributions are (C) by their respective contributors
#
#    All Rights Reserved
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
    """Run test to import MT940 RABO import."""

    def test_statement_import(self):
        """Test correct creation of single statement.

        For this test there is NOT an existing bank-account. Therefore a
        bank account should automatically be created in the main company.
        """
        partner_bank_model = self.env['res.partner.bank']
        import_model = self.registry('account.bank.statement.import')
        statement_model = self.registry('account.bank.statement')
        cr, uid = self.cr, self.uid
        statement_path = get_module_resource(
            'bank_statement_parse_nl_rabo_mt940',
            'test_files',
            'test-rabo.swi'
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
        # Check wether bank account has been created:
        vals = partner_bank_model.search(
            [('acc_number', '=', 'NL34RABO0142623393')])
        self.assertEquals(
            1, len(vals),
            'Bank account not created from statement'
        )
        # statement name is account number + '-' + date of last 62F line:
        ids = statement_model.search(
            cr, uid, [('name', '=', 'NL34RABO0142623393-2014-01-07')])
        self.assertTrue(ids, 'Statement not found after parse.')
        statement_id = ids[0]
        statement_obj = statement_model.browse(
            cr, uid, statement_id)
        self.assertTrue(
            abs(statement_obj.balance_start - 4433.52) < 0.00001,
            'Start balance %f not equal to 4433.52' %
            statement_obj.balance_start
        )
        self.assertTrue(
            abs(statement_obj.balance_end_real - 4798.91) < 0.00001,
            'Real end balance %f not equal to 4798.91' %
            statement_obj.balance_end_real
        )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
