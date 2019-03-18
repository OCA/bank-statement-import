# -*- coding: utf-8 -*-
# Copyright 2017 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
from datetime import timedelta
from odoo import fields
from odoo.addons.account.tests.account_test_classes import AccountingTestCase
from odoo.addons.account_bank_statement_import\
    .account_bank_statement_import import AccountBankStatementImport


class TestAccountBankStatementImportAutoReconcile(AccountingTestCase):
    def setUp(self):
        super(TestAccountBankStatementImportAutoReconcile, self).setUp()
        # we don't really have something to import, so we patch the
        # import routine to return what we want for our tests
        self.original_parse_file = AccountBankStatementImport._parse_file
        AccountBankStatementImport._parse_file = self._parse_file
        self.bank_account = self.env['res.partner.bank'].create({
            'acc_number': '42424242',
            'partner_id': self.env.ref('base.main_partner').id,
        })
        partner = self.env.ref('base.res_partner_2')
        self.invoice = self.env['account.invoice'].create({
            'partner_id': partner.id,
            'account_id': partner.property_account_receivable_id.id,
            'type': 'out_invoice',
        })
        self.invoice.with_context(
            journal_id=self.invoice.journal_id.id
        ).write({
            'invoice_line_ids': [(0, 0, {
                'name': '/',
                'price_unit': 42,
            })],
        })
        self.invoice.action_invoice_open()
        self.journal = self.env['account.journal'].create({
            'name': 'Journal for automatic reconciliations',
            'code': 'BNKAU',
            'type': 'bank',
            'bank_account_id': self.bank_account.id,
        })

    def tearDown(self):
        super(TestAccountBankStatementImportAutoReconcile, self).tearDown()
        AccountBankStatementImport._parse_file = self.original_parse_file

    def _parse_file(self, data):
        date = self.invoice.date_invoice
        return (
            self.invoice.company_id.currency_id.name,
            self.bank_account.acc_number,
            [{
                'name': 'Auto reconcile test',
                'date': fields.Date.to_string(
                    fields.Date.from_string(date) + timedelta(days=5)
                ),
                'transactions': [{
                    'name': self.invoice.number,
                    'date': fields.Date.to_string(
                        fields.Date.from_string(date) + timedelta(days=5)
                    ),
                    'amount': self.invoice.residual,
                    'unique_import_id': '42',
                    'account_number':
                    self.invoice.partner_id.bank_ids[:1].acc_number,
                }],
            }],
        )

    def test_account_bank_statement_import_auto_reconcile_odoo(self):
        self.env[
            'account.bank.statement.import.auto.reconcile.rule'
        ].create({
            'journal_id': self.journal.id,
            'rule_type': 'account.bank.statement.import.auto.reconcile.odoo',
        })
        self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode('hello world'),
            'auto_reconcile': True,
        }).import_file()
        # should find our move line
        self.assertEqual(self.invoice.state, 'paid')

    def test_account_bank_statement_import_auto_reconcile_exact_amount(self):
        rule = self.env[
            'account.bank.statement.import.auto.reconcile.rule'
        ].create({
            'journal_id': self.journal.id,
            'rule_type':
            'account.bank.statement.import.auto.reconcile.exact.amount',
            'match_st_name': True,
            'match_st_ref': True,
            'match_move_name': True,
            'match_move_ref': True,
            'match_line_name': True,
            'match_line_ref': True,
        })
        # first, we do an import with auto reconciliation turned off
        action = self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode('hello world'),
            'auto_reconcile': False,
        }).import_file()
        # nothing should have happened
        self.assertEqual(self.invoice.state, 'open')
        self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        ).unlink()
        # now we do matching, but manipulate the matching to work on the
        # ref field only which is empty in our example
        rule.write({'match_st_name': False})
        action = self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode('hello world'),
            'auto_reconcile': True,
        }).import_file()
        # nothing should have happened
        self.assertEqual(self.invoice.state, 'open')
        self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        ).unlink()
        # for exact amount matching, our first transaction should be matched
        # to the invoice's move line, marking the invoice as paid,
        # provided we allow matching by name
        rule.write({'match_st_name': True})
        action = self.env['account.bank.statement.import'].create({
            'data_file': base64.b64encode('hello world'),
            'auto_reconcile': True,
        }).import_file()
        # with the changed rules, we should have found a match
        self.assertEqual(self.invoice.state, 'paid')
        # undo reconciliations, reapply rules on the statement
        statement = self.env['account.bank.statement'].browse(
            action['context']['statement_ids']
        )
        statement.mapped(
            'line_ids.journal_entry_ids.line_ids'
        ).remove_move_reconcile()
        self.assertEqual(self.invoice.state, 'open')
        statement.mapped('line_ids.journal_entry_ids').write({
            'statement_line_id': False,
        })
        # fiddle a bit with the options
        rule.write({'case_sensitive': True})
        self.env['account.bank.statement.import.reapply.rules'].with_context(
            active_ids=statement.ids,
        ).create({}).action_reapply_rules()
        # we should have found the match from before
        self.assertEqual(self.invoice.state, 'paid')

    def test_rule_options(self):
        rule = self.env[
            'account.bank.statement.import.auto.reconcile.rule'
        ].create({
            'journal_id': self.journal.id,
            'rule_type':
            'account.bank.statement.import.auto.reconcile.exact.amount',
            'match_st_name': False,
        })
        # be sure our options are patched into the view
        fields_view = rule.fields_view_get(view_type='form')
        self.assertIn('match_st_name', fields_view['arch'])
        # check option values
        rules = rule.get_rules()
        # explicitly written
        self.assertFalse(rules.match_st_name)
        # defaults must be used here too
        self.assertTrue(rules.match_st_ref)
