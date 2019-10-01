# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import os
import base64
from odoo.tests import common


class TestTxtFile(common.TransactionCase):

    def setUp(self):
        super(TestTxtFile, self).setUp()

        self.map = self.env['account.bank.statement.import.map'].create({
            'name': 'Txt Map Test',
        })
        usd = self.env.ref('base.USD')
        self.journal = self.env['account.journal'].create({
            'name': 'Txt Bank',
            'type': 'bank',
            'code': 'TXT',
            'currency_id': (
                usd.id if self.env.user.company_id.currency_id != usd
                else False
            ),
        })

    def _do_import_xlsx(self, file_name):
        file_name = os.path.join(os.path.dirname(__file__), file_name)
        with open(file_name, 'rb') as fin:
            data = fin.read()
        return data

    def _do_import(self, file_name):
        file_name = os.path.join(os.path.dirname(__file__), file_name)
        return open(file_name).read()

    def test_import_header(self):
        file = self._do_import('sample_statement_en.csv')
        file = base64.b64encode(file.encode("utf-8"))
        wizard = self.env['wizard.txt.map.create'].with_context({
            'journal_id': self.journal.id,
            'active_ids': [self.map.id],
        }).create({'data_file': file})
        wizard.create_map_lines()
        self.assertEqual(len(self.map.map_line_ids.ids), 7)

    def test_import_txt_file(self):
        # Current statements before to run the wizard
        old_statements = self.env['account.bank.statement'].search([])
        # This journal is for Txt statements
        txt_map = self.env.ref(
            'account_bank_statement_import_txt_xlsx.txt_map'
        )
        self.journal.statement_import_txt_map_id = txt_map.id
        file = self._do_import('sample_statement_en.csv')
        file = base64.b64encode(file.encode("utf-8"))
        wizard = self.env['account.bank.statement.import'].with_context({
            'journal_id': self.journal.id,
        }).create({'data_file': file})
        wizard.import_file()
        staments_now = self.env['account.bank.statement'].search([])
        statement = staments_now - old_statements
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(len(statement.mapped('line_ids').filtered(
            lambda x: x.partner_id)), 1)
        self.assertAlmostEqual(
            sum(statement.mapped('line_ids.amount')), 1491.50
        )
        self.assertAlmostEqual(
            sum(statement.mapped('line_ids.amount_currency')), 1000.00
        )

    def test_import_xlsx_file(self):
        # Current statements before to run the wizard
        old_statements = self.env['account.bank.statement'].search([])
        # This journal is for Txt statements
        txt_map = self.env.ref(
            'account_bank_statement_import_txt_xlsx.txt_map'
        )
        self.journal.statement_import_txt_map_id = txt_map.id
        file = self._do_import_xlsx('sample_statement_en.xlsx')
        file = base64.b64encode(file)
        wizard = self.env['account.bank.statement.import'].with_context({
            'journal_id': self.journal.id,
        }).create({'data_file': file})
        wizard.import_file()
        staments_now = self.env['account.bank.statement'].search([])
        statement = staments_now - old_statements
        self.assertEqual(len(statement.line_ids), 2)
        self.assertEqual(len(statement.mapped('line_ids').filtered(
            lambda x: x.partner_id)), 1)
        self.assertAlmostEqual(
            sum(statement.mapped('line_ids.amount')), 1491.50
        )
        self.assertAlmostEqual(
            sum(statement.mapped('line_ids.amount_currency')), 1000.00
        )
