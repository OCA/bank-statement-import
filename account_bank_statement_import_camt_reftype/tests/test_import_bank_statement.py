# -*- coding: utf-8 -*-
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64

from openerp.tests.common import TransactionCase
from openerp.tools.misc import file_open


DATA_DIR = 'account_bank_statement_import_camt_reftype/test_files/'


class TestImport(TransactionCase):
    """Run test to import camt import."""

    def setUp(self):
        super(TestImport, self).setUp()
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'CH1111000000123456789',
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
        """Test that reference type is correctly imported."""
        with file_open(DATA_DIR + 'test-camt053-reftype') as testfile:
            data = testfile.read()
        action = self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode(data)
        }).import_file()
        statements = self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        )
        for line in statements.mapped('line_ids'):
            self.assertEqual(line.camt_ref_type, "ISR Reference")
