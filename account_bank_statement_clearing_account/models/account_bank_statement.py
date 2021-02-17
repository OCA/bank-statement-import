# Copyright 2017 Opener BV (<https://opener.amsterdam>)
# Copyright 2020 Vanmoof BV (<https://www.vanmoof.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class BankStatement(models.Model):
    _inherit = "account.bank.statement"

    def get_reconcile_clearing_account_lines(self):
        """ If this statement qualifies for clearing account reconciliation,
        return the relevant lines to (un)reconcile. This is the case if the
        default journal account is reconcilable, each statement line has a
        counterpart line on this account for the full amount and the sum of
        the counterpart lines is zero.
        """
        self.ensure_one()
        if (
            self.journal_id.default_debit_account_id
            != self.journal_id.default_credit_account_id
            or not self.journal_id.default_debit_account_id.reconcile
        ):
            return False
        account = self.journal_id.default_debit_account_id
        currency = self.journal_id.currency_id or self.company_id.currency_id

        def get_bank_line(st_line):
            for line in st_line.journal_entry_ids:
                field = "debit" if st_line.amount > 0 else "credit"
                if line.account_id == account and not currency.compare_amounts(
                    line[field], abs(st_line.amount)
                ):
                    return line
            return False

        move_lines = self.env["account.move.line"]
        for st_line in self.line_ids:
            bank_line = get_bank_line(st_line)
            if not bank_line:
                return False
            move_lines += bank_line
        balance = sum(line.debit - line.credit for line in move_lines)
        if not currency.is_zero(balance):
            return False
        return move_lines

    def reconcile_clearing_account(self):
        """ If applicable, reconcile the clearing account lines in case
        all lines are still unreconciled. """
        self.ensure_one()
        lines = self.get_reconcile_clearing_account_lines()
        if not lines or any(
            li.matched_debit_ids or li.matched_credit_ids for li in lines
        ):
            return False
        lines.reconcile()
        return True

    def unreconcile_clearing_account(self):
        """ If applicable, unreconcile the clearing account lines
        if still fully reconciled with each other. """
        self.ensure_one()
        lines = self.get_reconcile_clearing_account_lines()
        if not lines:
            return False
        reconciliation = lines[0].full_reconcile_id
        if reconciliation and lines == reconciliation.reconciled_line_ids:
            lines.remove_move_reconcile()
            return True
        return False

    def button_reopen(self):
        """ When setting the statement back to draft, unreconcile the
        reconciliation on the clearing account """
        res = super(BankStatement, self).button_reopen()
        for statement in self:
            statement.unreconcile_clearing_account()
        return res

    def button_confirm_bank(self):
        """ When confirming the statement, trigger the reconciliation of
        the lines on the clearing account (if applicable) """
        res = super(BankStatement, self).button_confirm_bank()
        for statement in self:
            statement.reconcile_clearing_account()
        return res
