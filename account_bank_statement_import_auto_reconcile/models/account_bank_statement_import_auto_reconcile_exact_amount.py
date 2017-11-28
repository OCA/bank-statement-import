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
    match_st_ref = fields.Boolean('Reference from st. line', default=True)
    match_st_name = fields.Boolean('Name from st. line', default=True)
    match_move_ref = fields.Boolean('Move reference', default=True)
    match_move_name = fields.Boolean('Move name', default=True)
    match_line_ref = fields.Boolean('Move line reference', default=True)
    match_line_name = fields.Boolean('Move line name', default=True)

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

        statement_fields = filter(None, [
            self.match_st_name and 'name' or None,
            self.match_st_ref and 'ref' or None,
        ])

        move_line_fields = filter(None, [
            self.match_move_ref and 'move_id.ref' or None,
            self.match_move_name and 'move_id.name' or None,
            self.match_line_ref and 'ref' or None,
            self.match_line_name and 'name' or None,
        ])

        domain = [
            ('reconcile_id', '=', False),
            ('state', '=', 'valid'),
            ('account_id.reconcile', '=', True),
            ('partner_id', '=', statement_line.partner_id.id),
            (amount_field, '=', self._round(sign * statement_line.amount)),
        ]

        domain += (
            len(statement_fields) * len(move_line_fields) - 1
        ) * ['|']

        for move_line_field in move_line_fields:
            for statement_field in statement_fields:
                value = statement_line[statement_field]
                domain.append((move_line_field, operator, value))

        move_lines = self.env['account.move.line'].search(domain, limit=2)
        if move_lines and len(move_lines) == 1:
            self._reconcile_move_line(statement_line, move_lines.id)
            return True
