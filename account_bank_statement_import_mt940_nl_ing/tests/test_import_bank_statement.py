# -*- coding: utf-8 -*-
# © 2015-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Run test to import MT940 IBAN ING import."""
from openerp.addons.account_bank_statement_import.tests import (
    TestStatementFile)


class TestImport(TestStatementFile):
    """Run test to import MT940 ING import."""

    def test_old_statement_import(self):
        """Test correct creation of single statement from old format."""
        self.create_fiscalyear(2014)
        self._test_statement_import(
            'account_bank_statement_import_mt940_nl_ing', 'test-ing-old.940',
            'NL77INGB0574908765-2014-01-20',
            start_balance=662.23, end_balance=564.35
        )

    def test_statement_import(self):
        """Test correct creation of single statement."""
        self.create_fiscalyear(2014)
        transactions = [
            {'remote_account': 'NL32INGB0000012345',
             'transferred_amount': 1.56,
             'value_date': '2014-02-20',
             'ref': 'EV12341REP1231456T1234', },
        ]
        self._test_statement_import(
            'account_bank_statement_import_mt940_nl_ing', 'test-ing.940',
            'NL77INGB0574908765-2014-02-20',
            start_balance=662.23, end_balance=564.35,
            transactions=transactions
        )
