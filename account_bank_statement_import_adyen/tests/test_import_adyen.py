# coding: utf-8
from openerp.addons.account_bank_statement_import.tests import (
    TestStatementFile)


class TestImportAdyen(TestStatementFile):
    def setUp(self):
        super(TestImportAdyen, self).setUp()
        self.journal = self.env['account.journal'].search(
            [('type', '=', 'bank')], limit=1)
        self.journal.default_debit_account_id.reconcile = True
        self.journal.write({
            'adyen_merchant_account': 'YOURCOMPANY_ACCOUNT',
            'update_posted': True,
        })

    def test_import_adyen(self):
        self._test_statement_import(
            'account_bank_statement_import_adyen', 'adyen_test.xlsx',
            'YOURCOMPANY_ACCOUNT 2016/48')
        statement = self.env['account.bank.statement'].search(
            [], order='create_date desc', limit=1)
        self.assertEqual(len(statement.line_ids), 22)
        self.assertTrue(
            self.env.user.company_id.currency_id.is_zero(
                sum(line.amount for line in statement.line_ids)))

        account = self.env['account.account'].search([(
            'type', '=', 'receivable')], limit=1)
        for line in statement.line_ids:
            line.process_reconciliation([{
                'debit': -line.amount if line.amount < 0 else 0,
                'credit': line.amount if line.amount > 0 else 0,
                'account_id': account.id}])

        statement.button_confirm_bank()
        self.assertEqual(statement.state, 'confirm')
        lines = self.env['account.move.line'].search([
            ('account_id', '=', self.journal.default_debit_account_id.id),
            ('statement_id', '=', statement.id)])
        reconcile = lines.mapped('reconcile_id')
        self.assertEqual(len(reconcile), 1)
        self.assertFalse(lines.mapped('reconcile_partial_id'))
        self.assertEqual(lines, reconcile.line_id)

        statement.button_draft()
        self.assertEqual(statement.state, 'draft')
        self.assertFalse(lines.mapped('reconcile_partial_id'))
        self.assertFalse(lines.mapped('reconcile_id'))

    def test_import_adyen_credit_fees(self):
        self._test_statement_import(
            'account_bank_statement_import_adyen',
            'adyen_test_credit_fees.xlsx',
            'YOURCOMPANY_ACCOUNT 2016/8')
