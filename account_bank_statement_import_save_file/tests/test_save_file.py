# -*- coding: utf-8 -*-
# © 2015 Therp BV (<http://therp.nl>).
# © 2017 Today Mourad EL HADJ MIMOUNE <mourad.elhadj.mimoune@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from odoo import api, models
from odoo.tests.common import TransactionCase


acc_number = 'BE1234567890'
module_name = 'account_bank_statement_import_save_file'


class HelloWorldParser(models.TransientModel):
    """ Fake parser that will return custom data if the file contains the
    name of the module. """
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        if module_name in data_file:
            return self._mock_parse(data_file)
        else:
            return super(HelloWorldParser, self)._parse_file(data_file)

    def _mock_parse(self, data_file):
        """ method that can be inherited in other tests to mock a statement
        parser. """
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
            .create({
                'data_file': base64.b64encode(bytes(
                    'account_bank_statement_import_save_file: Hello world'))
            })
        action = import_wizard_id.import_file()
        for statement in self.env['account.bank.statement'].browse(
                action['context']['statement_ids']):
            self.assertEqual(
                base64.b64decode(statement.import_file.datas),
                'account_bank_statement_import_save_file: Hello world')
