# -*- coding: utf-8 -*-
"""Run test to import MT940 IBAN RABO import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
    """Run test to import MT940 RABO import."""

    def test_statement_import(self):
        """Test correct creation of single statement."""
        transactions = [
            {
                'remote_account': 'NL66RABO0160878799',
                'transferred_amount': 400.00,
                'value_date': '2014-01-02',
                'ref': 'NONREF',
            },
        ]
        # statement name is account number + '-' + date of last 62F line:
        self._test_statement_import(
            'account_bank_statement_import_mt940_nl_rabo', 'test-rabo.swi',
            'NL34RABO0142623393-2014-01-07',
            local_account='NL34RABO0142623393',
            start_balance=4433.52, end_balance=4798.91,
            transactions=transactions
        )
