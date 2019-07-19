# Copyright 2019 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
import base64
from odoo.tests import common


class TestPaypalFile(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestPaypalFile, cls).setUpClass()

        cls.map = cls.env['account.bank.statement.import.paypal.map'].create({
            'name': 'Paypal Map Test',
        })
        cls.journal = cls.env['account.journal'].create({
            'name': 'Paypal Bank',
            'type': 'bank',
            'code': 'PYPAL',
        })

    def _do_import(self, file_name):
        file_name = os.path.join(os.path.dirname(__file__), file_name)
        return open(file_name).read()

    def test_import_header(self):
        file = self._do_import('paypal_en.csv')
        file = base64.b64encode(file.encode("utf-8"))
        wizard = self.env['wizard.paypal.map.create'].with_context({
            'journal_id': self.journal.id,
            'active_ids': [self.map.id],
        }).create({'data_file': file})
        wizard.create_map_lines()
        self.assertEqual(len(self.map.map_line_ids.ids), 18)

    def test_import_paypal_file(self):
        # Current statements before to run the wizard
        old_statements = self.env['account.bank.statement'].search([])
        # This journal is for Paypal statements
        paypal_map = self.env.ref(
            'account_bank_statement_import_paypal.paypal_map'
        )
        self.journal.paypal_map_id = paypal_map.id
        file = self._do_import('paypal_en.csv')
        file = base64.b64encode(file.encode("utf-8"))
        wizard = self.env['account.bank.statement.import'].with_context({
            'journal_id': self.journal.id,
        }).create({'data_file': file})
        wizard.import_file()
        staments_now = self.env['account.bank.statement'].search([])
        statement = staments_now - old_statements
        self.assertEqual(len(statement.line_ids), 3)
        self.assertEqual(len(statement.mapped('line_ids').filtered(
            lambda x: x.partner_id)), 1)
        self.assertAlmostEqual(
            sum(statement.mapped('line_ids.amount')), 1489.2
        )
