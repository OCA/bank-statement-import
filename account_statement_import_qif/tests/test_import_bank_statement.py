# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
import base64


class TestQifFile(TransactionCase):
    """Tests for import bank statement qif file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestQifFile, self).setUp()
        self.statement_import_model = self.env['account.bank.statement.import']
        self.statement_line_model = self.env['account.bank.statement.line']
        self.journal = self.env['account.journal'].create({
            'name': 'Test bank journal',
            'code': 'TEST',
            'type': 'bank',
        })
        self.partner = self.env['res.partner'].create({
            # Different case for trying insensitive case search
            'name': 'EPIC Technologies',
        })

    def test_qif_file_import(self):
        qif_file_path = get_module_resource(
            'account_bank_statement_import_qif', 'tests', 'test_qif.qif',
        )
        qif_file = base64.b64encode(open(qif_file_path, 'rb').read())
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal.id
        ).create(
            dict(data_file=qif_file)
        )
        wizard.import_file()
        statement = self.statement_line_model.search(
            [('name', '=', 'YOUR LOCAL SUPERMARKET')], limit=1,
        )[0].statement_id
        self.assertAlmostEqual(statement.balance_end_real, -1896.09, 2)
        line = self.statement_line_model.search(
            [('name', '=', 'Epic Technologies')], limit=1,
        )
        self.assertEqual(line.partner_id, self.partner)
