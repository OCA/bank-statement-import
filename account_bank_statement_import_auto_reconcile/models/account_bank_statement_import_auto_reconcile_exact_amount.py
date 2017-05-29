# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, fields, models


# pylint: disable=R7980
class AccountBankStatementImportAutoReconcileExactAmount(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.exact.amount'
    _description = 'Exact partner, amount and reference'

    substring_match = fields.Boolean('Match for substrings', default=False)
    case_sensitive = fields.Boolean('Case sensitive matching', default=False)

    @api.multi
    def reconcile(self, statement_line):
        if not statement_line.partner_id or (
            not statement_line.ref and not statement_line.name
        ):
            return

        operator = '=ilike'
        if self.substring_match:
            operator = 'substring_of'
        elif self.case_sensitive:
            operator = '=like'

        amount_field = 'debit'
        sign = 1
        if statement_line.currency_id or statement_line.journal_id.currency:
            amount_field = 'amount_currency'
        elif statement_line.amount < 0:
            amount_field = 'credit'
            sign = -1

        domain = [
            '|', '|', '|',
            ('ref', operator, statement_line.ref or ''),
            ('name', operator, statement_line.name or ''),
            ('ref', operator, statement_line.name or ''),
            ('name', operator, statement_line.ref or ''),
            ('reconcile_id', '=', False),
            ('state', '=', 'valid'),
            ('account_id.reconcile', '=', True),
            ('partner_id', '=', statement_line.partner_id.id),
            (amount_field, '=', self._round(sign * statement_line.amount)),
        ]
        move_lines = self.env['account.move.line'].search(domain, limit=2)
        if move_lines and len(move_lines)==1:
            self._reconcile_move_line(statement_line, move_lines.id)
            return True
