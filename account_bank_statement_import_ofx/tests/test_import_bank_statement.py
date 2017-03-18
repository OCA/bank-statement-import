# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


class TestOfxFile(TransactionCase):
    """Tests for import bank statement ofx file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestOfxFile, self).setUp()
        self.absi_model = self.env['account.bank.statement.import']
        self.abs_model = self.env['account.bank.statement']
        self.absl_model = self.env['account.bank.statement.line']
        cur = self.env.ref('base.USD')
        self.env.ref('base.main_company').currency_id = cur.id
        bank = self.env['res.partner.bank'].create({
            'acc_number': '123456',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
            })
        self.env['account.journal'].create({
            'name': 'Bank Journal TEST OFX',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            })

    def test_ofx_file_import(self):
        ofx_file_path = get_module_resource(
            'account_bank_statement_import_ofx',
            'tests/test_ofx_file/', 'test_ofx.ofx')
        ofx_file = open(ofx_file_path, 'rb').read().encode('base64')
        bank_statement = self.absi_model.create(
            dict(data_file=ofx_file))
        bank_statement.import_file()
        bank_st_record = self.abs_model.search(
            [('name', 'like', '123456')])[0]
        self.assertEquals(bank_st_record.balance_start, 2516.56)
        self.assertEquals(bank_st_record.balance_end_real, 2156.56)

        line = self.absl_model.search([
            ('name', '=', 'Agrolait'),
            ('statement_id', '=', bank_st_record.id)])[0]
        self.assertEquals(line.ref, '219378')
        self.assertEquals(line.date, '2013-08-24')
