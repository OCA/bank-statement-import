# -*- coding: utf-8 -*-
# Copyright 2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Run test to import camt.053 import."""
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

    def test_statement_import_batch(self):
        """Test aggregate import of batch statement."""
        transactions = [
            {
                # remote bank account will be left empty
                'transferred_amount': -664.05,
                'value_date': '2014-01-05',
                'ref': '2014/125',
            }
        ]
        bank = self.env.ref(
            'account_bank_statement_import_camt.camt_company_bank')
        bank.journal_id.camt_import_batch = True
        self._test_statement_import(
            'account_bank_statement_import_camt', 'test-camt053.xml',
            '2014-01-05-1234Test/1',
            local_account=bank.acc_number,
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
