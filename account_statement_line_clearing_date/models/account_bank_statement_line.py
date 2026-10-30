# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from xmlrpc.client import MAXINT

from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    clearing_date = fields.Date(
        index=True,
        copy=False,
        help="Date on which the transaction actually settled against the bank "
        "balance. If set, it drives the statement balance sequence instead of "
        "the accounting date.",
    )

    @api.depends("date", "sequence", "clearing_date")
    def _compute_internal_index(self):
        result = super()._compute_internal_index()
        st_lines = self.filtered(lambda line: line._origin.id and line.clearing_date)
        for st_line in st_lines:
            st_line.internal_index = (
                f'{st_line.clearing_date.strftime("%Y%m%d")}'
                f"{MAXINT - st_line.sequence:0>10}"
                f"{st_line._origin.id:0>10}"
            )
        return result
