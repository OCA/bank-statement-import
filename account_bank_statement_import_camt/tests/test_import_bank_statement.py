# -*- coding: utf-8 -*-
"""Run test to import camt.053 import."""
# © 2013-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
from openerp.tests.common import TransactionCase
from openerp.tools.misc import file_open


class TestImport(TransactionCase):
    """Run test to import camt import."""
    transactions = [
        {
            'account_number': 'NL46ABNA0499998748',
            'amount': -754.25,
            'date': '2014-01-05',
            'ref': '435005714488-ABNO33052620',
        },
    ]

    def test_statement_import(self):
        """Test correct creation of single statement."""
        action = {}
        with file_open(
            'account_bank_statement_import_camt/test_files/test-camt053'
        ) as testfile:
            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(testfile.read()),
            }).import_file()
        for statement in self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        ):
            self.assertTrue(any(
                all(
                    line[key] == self.transactions[0][key]
                    for key in ['amount', 'date', 'ref']
                ) and
                line.bank_account_id.acc_number ==
                self.transactions[0]['account_number']
                for line in statement.line_ids
            ))

    def test_zip_import(self):
        """Test import of multiple statements from zip file."""
        with file_open(
            'account_bank_statement_import_camt/test_files/test-camt053.zip'
        ) as testfile:
            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(testfile.read()),
            }).import_file()
        for statement in self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        ):
            self.assertTrue(statement.line_ids)
