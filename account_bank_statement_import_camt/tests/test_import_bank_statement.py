# -*- coding: utf-8 -*-
"""Run test to import camt.053 import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
from openerp.addons.account_bank_statement_import.tests import (
    TestStatementFile)


class TestImport(TestStatementFile):
    """Run test to import camt import."""

    def test_statement_import(self):
        """Test correct creation of single statement."""
        transactions = [
            {
                'remote_account': 'NL46ABNA0499998748',
                'transferred_amount': -754.25,
                'value_date': '2014-01-05',
                'ref': '435005714488-ABNO33052620',
            },
            {
                'remote_account': 'NL46ABNA0499998748',
                'transferred_amount': -564.05,
                'value_date': '2014-01-05',
                'ref': 'TESTBANK/NL/20141229/01206408',
            },
            {
                'remote_account': 'NL46ABNA0499998748',
                'transferred_amount': -100.0,
                'value_date': '2014-01-05',
                'ref': 'TESTBANK/NL/20141229/01206407',
            },
            {
                'remote_account': 'NL69ABNA0522123643',
                'transferred_amount': 1405.31,
                'value_date': '2014-01-05',
                'ref': '115',
            },
        ]
        self._test_statement_import(
            'account_bank_statement_import_camt', 'test-camt053.xml',
            '2014-01-05-1234Test/1',
            local_account='NL77ABNA0574908765',
            start_balance=15568.27, end_balance=15121.12,
            transactions=transactions
        )

    def test_zip_import(self):
        """Test import of multiple statements from zip file."""
        self._test_statement_import(
            'account_bank_statement_import_camt', 'test-camt053.zip',
            '2014-02-05-1234Test/2',  # Only name of first statement
            local_account='NL77ABNA0574908765',
        )
