# -*- coding: utf-8 -*-
"""Run test to import MT940 IBAN ING import."""
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
from openerp.addons.account_bank_statement_import.tests import (
    TestStatementFile)


class TestImport(TestStatementFile):
    """Run test to import MT940 ING import."""

    def test_old_statement_import(self):
        """Test correct creation of single statement from old format."""
        self._test_statement_import(
            'account_bank_statement_import_mt940_nl_ing', 'test-ing-old.940',
            'NL77INGB0574908765-2014-01-20',
            start_balance=662.23, end_balance=564.35
        )

    def test_statement_import(self):
        """Test correct creation of single statement."""
        transactions = [
            {
                'remote_account': 'NL32INGB0000012345',
                'transferred_amount': 1.56,
                'value_date': '2014-02-20',
                'ref': 'EV12341REP1231456T1234',
            },
        ]
        self._test_statement_import(
            'account_bank_statement_import_mt940_nl_ing', 'test-ing.940',
            'NL77INGB0574908765-2014-02-20',
            start_balance=662.23, end_balance=564.35,
            transactions=transactions
        )
