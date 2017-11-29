"""Run test to import camt.053 import."""
# © 2013-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


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
        """Test correct creation of single statement."""
        testfile = get_module_resource(
            'account_bank_statement_import_camt',
            'test_files',
            'test-camt053',
        )
        datafile = open(testfile, 'rb').read()
        action = self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode(datafile),
        }).import_file()
        for statement in self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        ):
            self.assertTrue(statement.name)
            self.assertEqual(statement.date, '2014-01-05')
            self.assertEqual(statement.difference, -504.16)
            self.assertEqual(statement.journal_type, 'bank')
            self.assertEqual(len(statement.line_ids), 3)
            for line in statement.line_ids:
                self.assertIn(line.amount, [1405.31, -594.05, -754.25])
                self.assertEqual(line.date, '2014-01-05')
                self.assertTrue(line.ref)
                self.assertTrue(line.journal_id)
                self.assertTrue(line.name)
                self.assertTrue(line.note)
                self.assertEqual(line.state, 'open')
                self.assertIn(
                    line.bank_account_id.acc_number,
                    ['NL69ABNA0522123643',
                     'NL46ABNA0499998748']
                )

    def test_zip_import(self):
        """Test import of multiple statements from zip file."""
        testfile = get_module_resource(
            'account_bank_statement_import_camt',
            'test_files',
            'test-camt053.zip',
        )
        datafile = open(testfile, 'rb').read()
        action = self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode(datafile),
        }).import_file()
        for statement in self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        ):
            self.assertTrue(statement.line_ids)
