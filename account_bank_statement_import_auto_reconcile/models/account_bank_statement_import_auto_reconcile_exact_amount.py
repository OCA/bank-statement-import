# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models
from openerp.tools import float_compare


class AccountBankStatementImportAutoReconcileExactAmount(models.AbstractModel):
    _inherit = 'account.bank.statement.import.auto.reconcile'
    _name = 'account.bank.statement.import.auto.reconcile.exact.amount'
    _description = 'Exact match on amount'

    @api.multi
    def reconcile(self, statement_line):
        """Find an open invoice for the statement line's partner"""
        # TODO: this is the lazy version, searching a bit more specialized
        # and with some caching should speed this up a lot
        matches = statement_line.get_reconciliation_proposition(statement_line)
        digits = self.env['decimal.precision'].precision_get('Account')
        if len(matches) == 1 and (
                float_compare(
                    matches[0]['debit'], statement_line.amount,
                    precision_digits=digits
                ) == 0 or
                float_compare(
                    -matches[0]['credit'], statement_line.amount,
                    precision_digits=digits
                ) == 0
        ):
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
            move_line_dict['counterpart_move_line_id'] = matches[0]['id']
            statement_line.process_reconciliation([move_line_dict])
            return True
