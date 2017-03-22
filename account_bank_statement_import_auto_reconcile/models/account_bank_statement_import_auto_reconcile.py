# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


class AccountBankStatementImportAutoReconcile(models.AbstractModel):
    """Inherit from this class and implement the reconcile function"""

    _name = 'account.bank.statement.import.auto.reconcile'
    _description = 'Base class for automatic reconciliation rules'

    wizard_id = fields.Many2one('account.bank.statement.import', required=True)
    # this is meant as a field to save options in and/or to carry state
    # between different reconciliations
    options = fields.Serialized('Options')

    @api.multi
    def reconcile(self, statement_line):
        """Will be called on your model, with wizard_id pointing
        to the currently open statement import wizard. If your rule consumes
        any options or similar, get the values from there.
        Return True if you reconciled this line, something Falsy otherwise"""
        raise NotImplementedError()
