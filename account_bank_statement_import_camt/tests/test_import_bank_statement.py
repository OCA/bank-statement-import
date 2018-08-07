# -*- coding: utf-8 -*-
"""Run test to import camt.053 import."""
# © 2013-2016 Therp BV <http://therp.nl>
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import difflib
import pprint
import tempfile

from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_open


DATA_DIR = 'account_bank_statement_import_camt/test_files/'


class TestParser(TransactionCase):
    """Tests for the camt parser itself."""
    def setUp(self):
        super(TestParser, self).setUp()
        self.parser = self.env['account.bank.statement.import.camt.parser']

    def _do_parse_test(self, inputfile, goldenfile):
        with file_open(inputfile) as testfile:
            data = testfile.read()
        res = self.parser.parse(data)
        with tempfile.NamedTemporaryFile(suffix='.pydata') as temp:
            pprint.pprint(res, temp)
            with file_open(goldenfile) as golden:
                temp.seek(0)
                diff = list(
                    difflib.unified_diff(golden.readlines(), temp.readlines(),
                                         golden.name,        temp.name))
                if len(diff) > 2:
                    self.fail(
                        "actual output doesn't match exptected output:\n%s" %
                        "".join(diff))

    def test_parse(self):
        self._do_parse_test(
            DATA_DIR + 'test-camt053',
            DATA_DIR + 'golden-camt053.pydata')

    def test_parse_txdtls(self):
        self._do_parse_test(
            DATA_DIR + 'test-camt053-txdtls',
            DATA_DIR + 'golden-camt053-txdtls.pydata')

    def test_parse_no_ntry(self):
        self._do_parse_test(
            DATA_DIR + 'test-camt053-no-ntry',
            DATA_DIR + 'golden-camt053-no-ntry.pydata',
        )


class TestImport(TransactionCase):
    """Run test to import camt import."""
    transactions = [
        {
            'account_number': 'NL46ABNA0499998748',
            'amount': -754.25,
            'date': '2014-01-05',
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

    def setUp(self):
        super(TestImport, self).setUp()
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'NL77ABNA0574908765',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.env['account.journal'].create({
            'name': 'Bank Journal - (test camt)',
            'code': 'TBNKCAMT',
            'type': 'bank',
            'bank_account_id': bank.id,
        })

    def test_statement_import(self):
        """Test correct creation of single statement."""
        action = {}
        with file_open(DATA_DIR + 'test-camt053') as testfile:
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
