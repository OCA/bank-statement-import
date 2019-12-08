# Copyright 2017 Onestein (<http://www.onestein.eu>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
import datetime
import re

from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


class TestImport(TransactionCase):
    """Run test to import mt940 import."""
    def setUp(self):
        super(TestImport, self).setUp()
        self.parser = self.env['account.bank.statement.import.mt940.parser']
        self.bank_account = self.env['res.partner.bank'].create({
            'acc_number': 'NL34RABO0142623393',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.journal = self.env['account.journal'].create({
            'name': 'Bank Journal - (test2 mt940)',
            'code': 'TBNK2MT940',
            'type': 'bank',
            'bank_account_id': self.bank_account.id,
            'currency_id': self.env.ref('base.EUR').id,
        })
        self.transactions = [
            {
                'amount': 400.00,
                'date': datetime.date(2014, 1, 2),
                'ref': False,
                'name': '/Test money paid by other partner:',
                'note': 'NONREFNL66RABO0160878799'
            },
            {
                'amount': -34.61,
                'date': datetime.date(2014, 1, 1),
                'ref': False,
                'name': '/Periode 01-10-2013 t/m 31-12-2013',
                'note': 'NONREF'
            }
        ]
        self.data = \
            "/BENM//NAME/Cost/REMI/Period 01-10-2013 t/m 31-12-2013/ISDT/20"
        self.codewords = ['BENM', 'ADDR', 'NAME', 'CNTP', 'ISDT', 'REMI']

    def test_get_methods(self):
        parser = parser = self.parser.with_context(type='mt940_general')
        # Test get_mt940_type
        self.assertEqual(parser.get_mt940_type(), 'mt940_general')
        # Test get_header_lines
        self.assertEqual(parser.get_header_lines(), 0)
        # Test get_header_regex
        self.assertEqual(parser.get_header_regex(), ':940:')
        # Test get_footer_regex
        self.assertEqual(parser.get_footer_regex(), '}')
        # Test get_tag_regex
        self.assertEqual(parser.get_tag_regex(), '^:[0-9]{2}[A-Z]*:')
        # Test get_codewords
        self.assertEqual(parser.get_codewords(),
                         ['BENM', 'ADDR', 'NAME', 'CNTP', 'ISDT', 'REMI'])
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
            'BENM': [''],
            'NAME': ['Cost'],
            'REMI': ['Period 01-10-2013 t', 'm 31-12-2013'],
            'ISDT': ['20'],
        }
        self.assertEqual(res, espected_res)

    def test_statement_import_rabo(self):
        """Test correct creation of single statement."""
        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-rabo.swi',
        )
        with open(testfile, 'rb') as datafile:
            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(datafile.read())
            }).import_file()
            statements = self.env['account.bank.statement'].browse(
                action['context']['statement_ids']
            )
            bank_st_record = statements[0]
            self.assertEqual(bank_st_record.balance_start, 4433.52)
            self.assertEqual(bank_st_record.balance_end_real, 4833.52)
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
            bank_st_record = statements[1]
            self.assertEqual(bank_st_record.balance_start, 4833.52)
            self.assertEqual(bank_st_record.balance_end_real, 4798.91)
            statement_line = bank_st_record.line_ids[0]
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

    def test_wrong_file_import(self):
        """Test wrong file import."""
        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-wrong-file.940',
        )
        parser = self.parser.with_context(type='mt940_general')
        datafile = open(testfile, 'rb').read()
        with self.assertRaises(ValueError):
            parser.parse(datafile)

    def test_parse_file(self):
        testfile = get_module_resource(
            'account_bank_statement_import_mt940_base',
            'test_files',
            'test-rabo.swi',
        )
        with open(testfile, 'rb') as datafile:
            parser = self.parser.with_context(type='mt940_general')
            datafile = open(testfile, 'rb').read()
            self.assertEqual(
                parser.parse(datafile),
                ('EUR',
                 'NL34RABO0142623393',
                 [{'name': None, 'date': None, 'balance_start': 0.0,
                   'balance_end_real': 0.0, 'transactions': []},
                  {'name': 'NL34RABO0142623393',
                   'date': datetime.datetime(2014, 1, 2, 0, 0),
                   'balance_start': 4433.52,
                   'balance_end_real': 4833.52,
                   'transactions': [
                       {'date': datetime.datetime(2014, 1, 2, 0, 0),
                        'amount': 400.0,
                        'note': 'NONREFNL66RABO0160878799',
                        'name': '/Test money paid by other partner:'}]},
                  {'name': 'NL34RABO0142623393',
                   'date': datetime.datetime(2014, 1, 3, 0, 0),
                   'balance_start': 4833.52,
                   'balance_end_real': 4833.52,
                   'transactions': []},
                  {'name': 'NL34RABO0142623393',
                   'date': datetime.datetime(2014, 1, 6, 0, 0),
                   'balance_start': 4833.52,
                   'balance_end_real': 4798.91,
                   'transactions': [
                       {'date': datetime.datetime(2014, 1, 1, 0, 0),
                        'amount': -34.61,
                        'note': 'NONREF',
                        'name': '/Periode 01-10-2013 t/m 31-12-2013'}]},
                  {'name': 'NL34RABO0142623393',
                   'date': datetime.datetime(2014, 1, 7, 0, 0),
                   'balance_start': 4798.91,
                   'balance_end_real': 4798.91,
                   'transactions': []}]))
