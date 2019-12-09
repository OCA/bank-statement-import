# -*- coding: utf-8 -*-
# Copyright (C) 2013-2015 Therp BV <http://therp.nl>
# Copyright 2019 OdooERP Romania <https://odooerpromania.ro>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import datetime
import re

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
            "/RTRN/MS03//EREF/20120501P0123478//MARF/MND" \
            "-" \
            "120123//CSID/NL32" \
            "ZZZ999999991234//CNTP/NL32INGB0000012345/INGBNL2A/J.Janssen" \
            "///REMI/USTD//CO" \
            "NTRIBUTIE FEB 2014/"
        self.codewords = ['RTRN', 'BENM', 'ORDP', 'CSID', 'BUSP', 'MARF',
                          'EREF', 'PREF', 'REMI', 'ID', 'PURP', 'ULTB',
                          'ULTD', 'CREF', 'IREF', 'CNTP', 'ULTC', 'EXCH',
                          'CHGS']

    def test_get_methods(self):
        parser = parser = self.parser.with_context(type='mt940_nl_ing')
        # Test get_mt940_type
        self.assertEqual(parser.get_mt940_type(), 'mt940_nl_ing')
        # Test get_header_lines
        self.assertEqual(parser.get_header_lines(), 0)
        # Test get_header_regex
        self.assertEqual(parser.get_header_regex(),
                         '^0000 01INGBNL2AXXXX|^{1')
        # Test get_footer_regex
        self.assertEqual(parser.get_footer_regex(), '^-}$|^-XXX$')
        # Test get_tag_regex
        self.assertEqual(parser.get_tag_regex(), '^:[0-9]{2}[A-Z]*:')
        # Test get_codewords
        self.assertEqual(parser.get_codewords(),
                         ['RTRN', 'BENM', 'ORDP', 'CSID', 'BUSP', 'MARF',
                          'EREF', 'PREF', 'REMI', 'ID', 'PURP', 'ULTB',
                          'ULTD', 'CREF', 'IREF', 'CNTP', 'ULTC', 'EXCH',
                          'CHGS'])
        # Test get_tag_61_regex
        tag_61_regex = re.compile(
            r'^(?P<date>\d{6})(?P<line_date>\d{0,4})'
            r'(?P<sign>[CD])(?P<amount>\d+,\d{2})N(?P<type>.{3})'
            r'(?P<reference>\w{1,50})'
        )
        self.assertEqual(parser.get_tag_61_regex(), tag_61_regex)
        # Test parse_amount
        self.assertEqual(parser.parse_amount('D', '123,41'), -123.41)
        self.assertEqual(parser.parse_amount('C', '123,41'), 123.41)
        # Test get_subfields
        res = parser.get_subfields(self.data, self.codewords)
        espected_res = {
            'CNTP': ['NL32INGB0000012345', 'INGBNL2A', 'J.Janssen', '', ''],
            'CSID': ['NL32ZZZ999999991234', ''],
            'EREF': ['20120501P0123478', ''],
            'MARF': ['MND-120123', ''],
            'REMI': ['USTD', '', 'CONTRIBUTIE FEB 2014', ''],
            'RTRN': ['MS03', '']
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
