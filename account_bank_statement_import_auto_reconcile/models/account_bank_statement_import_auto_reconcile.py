# -*- coding: utf-8 -*-
# Copyright 2017 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tools import float_compare, float_round
from odoo import api, fields, models


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
        """ Given a bank statement line and an account move line (Journal Item)
        which we know that can be reconciled, reconcile them.

        :param statement_line: The account.bank.statement.line to reconcile.
        :param move_line_id: The id of the account.move.line to reconcile.
        """
        acc_move_line = self.env['account.move.line']
        acc_move = self.env['account.move']
        move = acc_move.create(statement_line._prepare_reconciliation_move(
            statement_line.ref))
        move_line_dict = statement_line._prepare_reconciliation_move_line(
            move,
            -acc_move_line.browse(move_line_id).balance,
        )
        move_line = acc_move_line.with_context(
            check_move_validity=False).create(move_line_dict)
        move_line_dict.update({'move_line': move_line})
        statement_line.process_reconciliation(
            counterpart_aml_dicts=[move_line_dict])

    @api.multi
    def reconcile(self, statement_line):
        """Will be called on your model, with wizard_id pointing
        to the currently open statement import wizard. If your rule consumes
        any options or similar, get the values from there.
        Return True if you reconciled this line, something Falsy otherwise"""
        raise NotImplementedError()
