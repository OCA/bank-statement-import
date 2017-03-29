# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp.tools import float_compare, float_round
from openerp import api, fields, models


class AccountBankStatementImportAutoReconcile(models.AbstractModel):
    """Inherit from this class and implement the reconcile function"""

    _name = 'account.bank.statement.import.auto.reconcile'
    _description = 'Base class for automatic reconciliation rules'

    wizard_id = fields.Many2one('account.bank.statement.import', required=True)
    # this is meant as a field to save options in and/or to carry state
    # between different reconciliations
    options = fields.Serialized('Options')

    @property
    def _digits(self):
        try:
            return self.__digits
        except:
            self.__digits = self.env['decimal.precision'].precision_get(
                'Account'
            )
            return self.__digits

    @api.model
    def _round(self, value):
        return float_round(value, precision_digits=self._digits)

    @api.model
    def _matches_amount(self, statement_line, debit, credit):
        """helper to compare if an amount matches some move line data"""
        return (
            float_compare(
                debit, statement_line.amount,
                precision_digits=self._digits
            ) == 0 or
            float_compare(
                -credit, statement_line.amount,
                precision_digits=self._digits
            ) == 0
        )

    @api.model
    def _reconcile_move_line(self, statement_line, move_line_id):
        """Helper to reconcile some move line with a bank statement.
        This will create a move to reconcile with and assigns journal_entry_id
        """
        move = self.env['account.move'].create(
            self.env['account.bank.statement']._prepare_move(
                statement_line,
                (
                    statement_line.statement_id.name or statement_line.name
                ) + "/" + str(statement_line.sequence or '')
            )
        )
        move_line_dict = self.env['account.bank.statement']\
            ._prepare_bank_move_line(
                statement_line, move.id, -statement_line.amount,
                statement_line.statement_id.company_id.currency_id.id,
            )
        move_line_dict['counterpart_move_line_id'] = move_line_id
        statement_line.process_reconciliation([move_line_dict])

    @api.multi
    def reconcile(self, statement_line):
        """Will be called on your model, with wizard_id pointing
        to the currently open statement import wizard. If your rule consumes
        any options or similar, get the values from there.
        Return True if you reconciled this line, something Falsy otherwise"""
        raise NotImplementedError()
