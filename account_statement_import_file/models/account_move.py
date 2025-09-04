from odoo import api, models


class AccountMove(models.Model):
    _inherit = "account.move"

    @api.depends("journal_id", "statement_line_id")
    def _compute_currency_id(self):
        res = super()._compute_currency_id()
        if self.env.context.get("from_stmt_import", False):
            for invoice in self:
                if (
                    invoice.statement_line_id.foreign_currency_id
                    and invoice.statement_line_id.foreign_currency_id
                    == invoice.journal_id.company_id.currency_id
                ):
                    currency = (
                        invoice.journal_id.currency_id
                        or invoice.statement_line_id.foreign_currency_id
                        or invoice.currency_id
                        or invoice.journal_id.company_id.currency_id
                    )
                    invoice.currency_id = currency
        return res
