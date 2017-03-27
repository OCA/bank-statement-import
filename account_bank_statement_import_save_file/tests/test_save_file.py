# -*- coding: utf-8 -*-
# © 2015 Therp BV (<http://therp.nl>).
# © 2017 Today Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from odoo import api, models
from odoo.tests.common import TransactionCase


acc_number = 'BE1234567890'


class HelloWorldParser(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        return (
            'EUR',
            acc_number,
            [{
                'name': '000000123',
                'date': '2013-06-26',
                'transactions': [{
                    'name': 'KBC-INVESTERINGSKREDIET 787-5562831-01',
                    'date': '2013-06-26',
                    'amount': 42,
                    'unique_import_id': 'hello',
                }],
            }],
        )


class TestSaveFile(TransactionCase):
    def setUp(self):
        super(TestSaveFile, self).setUp()
        self.currency_eur_id = self.env.ref("base.EUR").id
        self.bank_journal_euro = self.env['account.journal'].create(
            {'name': 'Bank',
             'type': 'bank',
             'code': 'BNK_test_imp',
             'currency_id': self.currency_eur_id
             })

    def test_SaveFile(self):
        HelloWorldParser._build_model(self.registry, self.cr)
        import_wizard = self.env['account.bank.statement.import']
        journal_id = self.bank_journal_euro.id
        import_wizard_id = import_wizard.with_context(journal_id=journal_id)\
            .create(
                {'data_file': base64.b64encode(bytes('Hello world'))})
        action = import_wizard_id.import_file()
        for statement in self.env['account.bank.statement'].browse(
                action['context']['statement_ids']):
            self.assertEqual(
                base64.b64decode(statement.import_file.datas),
                'Hello world')
