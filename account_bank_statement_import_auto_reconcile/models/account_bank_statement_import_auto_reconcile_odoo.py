# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models


class AccountBankStatementImportAutoReconcileOdoo(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.odoo'
    _description = 'Odoo standard'

    @api.multi
    def reconcile(self, statement_line):
        """Find an open invoice for the statement line's partner"""
        matches = statement_line.get_reconciliation_proposition(statement_line)
        if len(matches) == 1 and self._matches_amount(
                statement_line, matches[0]['debit'], -matches[0]['credit'],
        ):
            self._reconcile_move_line(statement_line, matches[0]['id'])
            return True
