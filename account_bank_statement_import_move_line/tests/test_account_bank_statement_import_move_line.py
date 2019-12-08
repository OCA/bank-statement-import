# -*- coding: utf-8 -*-
# Copyright 2017 Tecnativa - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from odoo.tests import common
from odoo import fields


class TestAccountBankStatementImportMoveLine(common.SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestAccountBankStatementImportMoveLine, cls).setUpClass()
        cls.account_type = cls.env['account.account.type'].create({
            'name': 'Test Account Type'})
        cls.a_receivable = cls.env['account.account'].create({
            'code': 'TAA',
            'name': 'Test Receivable Account',
            'internal_type': 'receivable',
            'user_type_id': cls.account_type.id,
        })
        cls.partner = cls.env['res.partner'].create({
            'name': 'Test Partner 2',
            'parent_id': False,
        })
        cls.journal = cls.env['account.journal'].create({
            'name': 'Test Journal',
            'type': 'bank',
        })
        cls.invoice = cls.env['account.invoice'].create({
            'name': 'Test Invoice 3',
            'partner_id': cls.partner.id,
            'type': 'out_invoice',
            'journal_id': cls.journal.id,
            'invoice_line_ids': [(0, 0, {
                'account_id': cls.a_receivable.id,
                'name': 'Test line',
                'quantity': 1.0,
                'price_unit': 100.00,
            })],
        })
        cls.statement = cls.env['account.bank.statement'].create({
            'journal_id': cls.journal.id})

    def test_global(self):
        self.invoice.action_invoice_open()
        self.assertTrue(self.invoice.move_id)
        self.invoice.move_id.post()
        wizard_o = self.env['account.statement.line.create']
        context = wizard_o._context.copy()
        context.update({
            'active_model': 'account.bank.statement',
            'active_id': self.statement.id,
        })
        wizard = wizard_o.with_context(context).create({
            'statement_id': self.statement.id,
            'partner_id': self.partner.id,
            'journal_ids': [(4, self.journal.id)],
            'allow_blocked': True,
            'date_type': 'move',
            'move_date': fields.Date.today(),
            'invoice': False,
        })
        wizard.populate()
        self.assertTrue(len(wizard.move_line_ids), 2)
        wizard.invoice = True
        wizard.move_line_filters_change()
        wizard.populate()
        self.assertTrue(len(wizard.move_line_ids), 1)
        line = wizard.move_line_ids[0]
        self.assertEqual(line.debit, self.invoice.amount_total)
        wizard.create_statement_lines()
        line = self.statement.line_ids[0]
        self.assertEqual(line.amount, self.invoice.amount_total)
