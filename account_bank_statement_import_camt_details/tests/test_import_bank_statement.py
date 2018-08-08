# -*- coding: utf-8 -*-
# © 2017 CompassionCH <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_open


class TestImport(TransactionCase):
    """Run test to import camt import."""

    def setUp(self):
        super(TestImport, self).setUp()
        bank = self.env['res.partner.bank'].create({
            'acc_number': 'NL77ABNA0574908765',
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
        """Test that transaction details are correctly imported."""
        line_details = [
            {
                'partner_account': 'NL69ABNA0522123643',
                'partner_bic': 'ABNANL2A',
                'partner_name': '3rd party Media',
                'partner_address': 'SOMESTREET 570-A, 1276 ML HOUSCITY'
            },
            {
                'partner_account': 'NL46ABNA0499998748',
                'partner_bic': 'ABNANL2A',
                'partner_name': 'Test Customer',
            },
            {
                'partner_account': 'NL46ABNA0499998748',
                'partner_bic': 'ABNANL2A',
                'partner_name': 'Test Customer',
            },
            {
                'partner_account': 'NL46ABNA0499998748',
                'partner_bic': 'ABNANL2A',
                'partner_name': 'INSURANCE COMPANY TESTX',
                'partner_address': 'TEST STREET 20, 1234 AB TESTCITY'
            },
        ]
        with file_open(
            'account_bank_statement_import_camt/test_files/test-camt053'
        ) as testfile:
            action = self.env['account.bank.statement.import'].create({
                'data_file': base64.b64encode(testfile.read()),
            }).import_file()
        statement_lines = self.env['account.bank.statement'].browse(
            action['context']['statement_ids']).mapped('line_ids')
        for i in range(0, len(line_details)):
            line = statement_lines[i]
            rec_data = line.get_statement_line_for_reconciliation_widget()
            for key, val in line_details[i].iteritems():
                # test data is in reconcile data view
                if key in ('partner_account', 'partner_address'):
                    self.assertEqual(val, rec_data.get(key))
                # test field is set in model
                self.assertEqual(getattr(line, key), val)
