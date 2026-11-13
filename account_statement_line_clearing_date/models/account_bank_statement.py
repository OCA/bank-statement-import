# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    @api.depends("line_ids.internal_index", "line_ids.state", "line_ids.clearing_date")
    def _compute_date_index(self):
        res = super()._compute_date_index()
        for stmt in self:
            st_lines = stmt.line_ids.filtered(
                lambda line: line.internal_index and line.state == "posted"
            )
            last = st_lines.sorted("internal_index")[-1:]
            if last.clearing_date and last.clearing_date != last.date:
                stmt.date = last.clearing_date
        return res
