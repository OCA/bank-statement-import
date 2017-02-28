# coding: utf-8
from openerp import api, models


class BankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.multi
    def get_reconcile_clearing_account_lines(self):
        if (self.journal_id.default_debit_account_id !=
                self.journal_id.default_credit_account_id or
                not self.journal_id.default_debit_account_id.reconcile):
            return False
        account = self.journal_id.default_debit_account_id
        currency = self.journal_id.currency or self.company_id.currency_id

        def get_bank_line(st_line):
            for line in st_line.journal_entry_id.line_id:
                if st_line.amount > 0:
                    compare_amount = st_line.amount
                    field = 'debit'
                else:
                    compare_amount = -st_line.amount
                    field = 'credit'
                if (line[field] and
                        not currency.compare_amounts(
                            line[field], compare_amount) and
                        line.account_id == account):
                    return line
            return False

        move_lines = self.env['account.move.line']
        for st_line in self.line_ids:
            bank_line = get_bank_line(st_line)
            if not bank_line:
                return False
            move_lines += bank_line
        balance = sum(line.debit - line.credit for line in move_lines)
        if not currency.is_zero(balance):
            return False
        return move_lines

    @api.multi
    def reconcile_clearing_account(self):
        self.ensure_one()
        lines = self.get_reconcile_clearing_account_lines()
        if not lines:
            return False
        if any(line.reconcile_id or line.reconcile_partial_id
               for line in lines):
            return False
        lines.reconcile_partial()

    @api.multi
    def unreconcile_clearing_account(self):
        self.ensure_one()
        lines = self.get_reconcile_clearing_account_lines()
        if not lines:
            return False
        reconciliation = lines[0].reconcile_id
        if reconciliation and all(
                line.reconcile_id == reconciliation
                for line in lines) and all(
                    line in lines
                    for line in reconciliation.line_id):
            reconciliation.unlink()

    @api.multi
    def button_draft(self):
        res = super(BankStatement, self).button_draft()
        for statement in self:
            statement.unreconcile_clearing_account()
        return res

    @api.multi
    def button_confirm_bank(self):
        res = super(BankStatement, self).button_confirm_bank()
        for statement in self:
            statement.reconcile_clearing_account()
        return res
