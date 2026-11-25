# Copyright 2017 Tecnativa - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

from odoo import models


class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    def _prepare_statement_line_vals(self, statement):
        self.ensure_one()
        amount = 0.0
        if self.debit > 0:
            amount = self.debit
        elif self.credit > 0:
            amount = -self.credit
        vals = {
            "name": self.name or "?",
            "amount": amount,
            "partner_id": self.partner_id.id,
            "statement_id": statement.id,
            "payment_ref": self.ref or self.name,
            "date": self.date_maturity,
            "currency_id": self.currency_id.id,
        }
        if statement.currency_id != self.currency_id:
            vals.update(
                {
                    "amount_currency": self.amount_currency,
                }
            )
        return vals

    def create_statement_line_from_move_line(self, statement):
        abslo = self.env["account.bank.statement.line"]
        for mline in self:
            abslo.create(mline._prepare_statement_line_vals(statement))
        return
