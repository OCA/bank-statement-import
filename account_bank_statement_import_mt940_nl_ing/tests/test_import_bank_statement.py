# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 Therp BV <http://therp.nl>
# Copyright 2019 OdooERP Romania <https://odooerpromania.ro>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import datetime

from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


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
            {'date': datetime.date(2014, 2, 20),
             'amount': 1.56,
             'note': 'EREF',
             'account_number': 'NL32INGB0000012345',
             'partner_name': 'ING BANK NV INZAKE WEB',
             'name': '/EV10001REP1000000T1000EV12341REP1231456T1234'},
            {'date': datetime.date(2014, 2, 20),
             'amount': -1.57,
             'note': 'PREF',
             'name': '/TOTAAL 1 VZ'},
            {'date': datetime.date(2014, 2, 20),
             'amount': 1.57,
             'note': 'EREF',
             'account_number': 'NL32INGB0000012345',
             'partner_name': 'J.Janssen',
             'name': '/Factuurnr 123456 Klantnr 0012320120123456789'},
            {'date': datetime.date(2014, 2, 20),
             'amount': -1.14,
             'note': 'EREF',
             'account_number': 'NL32INGB0000012345',
             'partner_name': 'ING Bank N.V. inzake WeB',
             'name': '/EV123REP123412T1234EV123REP123412T1234'},
            {'date': datetime.date(2014, 2, 20),
             'amount': 1.45,
             'note': 'PREF',
             'name': '/TOTAAL 1 POSTEN'},
            {'date': datetime.date(2014, 2, 20),
             'amount': -12.75,
             'note': 'EREF',
             'account_number': 'NL32INGB0000012345',
             'partner_name': 'J.Janssen',
             'name': '/CONTRIBUTIE FEB 201420120501P0123478'},
            {'date': datetime.date(2014, 2, 20),
             'amount': 32.0,
             'note': '9001123412341234',
             'account_number': 'NL32INGB0000012345',
             'partner_name': 'J.Janssen',
             'name': '/900112341234123415814016000676480'},
            {'date': datetime.date(2014, 2, 20),
             'amount': -119.0,
             'note': '1070123412341234',
             'account_number': 'NL32INGB0000012345',
             'partner_name': 'INGBANK NV',
             'name': '/107012341234123415614016000384600'}
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
            keys = ['date', 'amount', 'note', 'account_number',
                    'partner_name', 'name']
            self.assertEqual(len(self.transactions),
                             len(bank_st_record.line_ids))
            for i in range(len(self.transactions)):
                transaction = self.transactions[i]
                line = bank_st_record.line_ids.sorted(reverse=True)[i]
                for key in keys:
                    if transaction.get(key):
                        self.assertEqual(transaction[key],
                                         line.read([key])[0][key])
