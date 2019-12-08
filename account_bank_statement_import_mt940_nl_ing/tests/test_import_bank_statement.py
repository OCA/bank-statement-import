# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 Therp BV <http://therp.nl>
# Copyright 2019 OdooERP Romania <https://odooerpromania.ro>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import datetime

from odoo.tests.common import TransactionCase, tagged
from odoo.modules.module import get_module_resource


@tagged('-standard', 'mt940')
class TestImport(TransactionCase):
    """Run test to import MT940 ING import."""

    def setUp(self):
        super(TestImport, self).setUp()
        self.parser = self.env['account.bank.statement.import.mt940.parser']
        self.bank_account = self.env['res.partner.bank'].create({
            'acc_number': 'NL77INGB0574908765',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.journal = self.env['account.journal'].create({
            'name': 'Bank Journal - (test ing mt940)',
            'code': 'TBNK2MT940',
            'type': 'bank',
            'bank_account_id': self.bank_account.id,
            'currency_id': self.env.ref('base.EUR').id,
        })
        self.transactions = [
            {
                'remote_account': 'NL32INGB0000012345',
                'transferred_amount': 1.56,
                'value_date': '2014-02-20',
                'ref': 'EV12341REP1231456T1234',
            },
            {
                'remote_account': 'NL32INGB0000012345',
                'transferred_amount': 1.56,
                'value_date': '2014-02-20',
                'ref': 'EV12341REP1231456T1234',
            }
        ]
        self.data = \
            "/BENM//NAME/Cost/REMI/Period 01-10-2013 t/m 31-12-2013/ISDT/20"
        self.codewords = ['BENM', 'ADDR', 'NAME', 'CNTP', 'ISDT', 'REMI']

    def test_get_subfields(self):
        """Unit Test function get_subfields()."""

        res = self.parser.get_subfields(self.data, self.codewords)
        espected_res = {
            'BENM': [''],
            'NAME': ['Cost'],
            'REMI': ['Period 01-10-2013 t', 'm 31-12-2013'],
            'ISDT': ['20'],
        }
        self.assertEqual(res, espected_res)

    def test_statement_import_ing(self):
        """Test correct creation of single statement."""
        testfile = get_module_resource(
            'account_bank_statement_import_mt940_nl_ing',
            'test_files',
            'test-ing.940',
        )
        with open(testfile, 'rb') as datafile:
            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(datafile.read())
            }).import_file()
            statements = self.env['account.bank.statement'].browse(
                action['context']['statement_ids']
            )
            bank_st_record = statements[0]
            self.assertEqual(bank_st_record.balance_start, 662.23)
            self.assertEqual(bank_st_record.balance_end_real, 564.35)
            statement_line = bank_st_record.line_ids[0]
            self.assertEqual(statement_line.amount,
                             self.transactions[0]['amount'])
            self.assertEqual(statement_line.date,
                             self.transactions[0]['date'])
            self.assertEqual(statement_line.ref,
                             self.transactions[0]['ref'])
            self.assertEqual(statement_line.name,
                             self.transactions[0]['name'])
            self.assertEqual(statement_line.note,
                             self.transactions[0]['note'])
            statement_line = bank_st_record.line_ids[1]
            self.assertEqual(statement_line.amount,
                             self.transactions[1]['amount'])
            self.assertEqual(statement_line.date,
                             self.transactions[1]['date'])
            self.assertEqual(statement_line.ref,
                             self.transactions[1]['ref'])
            self.assertEqual(statement_line.name,
                             self.transactions[1]['name'])
            self.assertEqual(statement_line.note,
                             self.transactions[1]['note'])
