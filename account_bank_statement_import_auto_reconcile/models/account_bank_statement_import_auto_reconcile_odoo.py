# -*- coding: utf-8 -*-
# Copyright 2017 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class AccountBankStatementImportAutoReconcileOdoo(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.odoo'
    _description = 'Odoo standard'

    @api.multi
    def reconcile(self, statement_line):
        """ Reconcile the given statement line with the appropriate
        account move line.

        :param statement_line: The account.bank.statement.line to reconcile.
        """
        matches = statement_line.get_reconciliation_proposition()
        if len(matches) == 1 and self._matches_amount(
                statement_line, matches[0]['debit'], -matches[0]['credit'],
        ):
            self._reconcile_move_line(statement_line, matches[0]['id'])
            return True
