# -*- coding: utf-8 -*-
# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource


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
            'qif_date_format': 'mdy'
        })
        self.journal_dmy = self.env['account.journal'].create({
            'name': 'Test bank journal DMY',
            'code': 'TEST_DMY',
            'type': 'bank',
            'qif_date_format': 'dmy'
        })
        self.journal_ymd = self.env['account.journal'].create({
            'name': 'Test bank journal YMD',
            'code': 'TEST_YMD',
            'type': 'bank',
            'qif_date_format': 'ymd'
        })
        self.partner = self.env['res.partner'].create({
            # Different case for trying insensitive case search
            'name': 'EPIC Technologies',
        })

    def test_qif_file_import(self):
        qif_file_path = get_module_resource(
            'account_bank_statement_import_qif',
            'test_files',
            'test_qif.qif',
        )
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
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

    def test_date_format_mdy(self):
        qif_file_path = get_module_resource(
            'account_bank_statement_import_qif',
            'test_files',
            'test_qif.qif',
        )
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal.id
        ).create(
            dict(data_file=qif_file)
        )
        wizard.import_file()
        line = self.statement_line_model.search(
            [('name', '=', 'Delta PC')], limit=1,
        )
        self.assertEqual(line.date, '2013-08-12')

    def test_date_format_dmy(self):
        qif_file_path = get_module_resource(
            'account_bank_statement_import_qif',
            'test_files',
            'test_qif_dmy.qif',
        )
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal_dmy.id
        ).create(
            dict(data_file=qif_file)
        )
        wizard.import_file()
        line = self.statement_line_model.search(
            [('name', '=', 'Delta PC')], limit=1,
        )
        self.assertEqual(line.date, '2013-08-12')

    def test_date_format_ymd(self):
        qif_file_path = get_module_resource(
            'account_bank_statement_import_qif',
            'test_files',
            'test_qif_ymd.qif',
        )
        qif_file = open(qif_file_path, 'rb').read().encode('base64')
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal_ymd.id
        ).create(
            dict(data_file=qif_file)
        )
        wizard.import_file()
        line = self.statement_line_model.search(
            [('name', '=', 'Delta PC')], limit=1,
        )
        self.assertEqual(line.date, '2013-08-12')
