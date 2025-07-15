# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from xmlrpc.client import MAXINT

from odoo import api, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    @api.depends("journal_id.statement_line_internal_index")
    def _compute_internal_index(self):  # pylint: disable=missing-return
        # Compute the internal index based on the defined order
        line_ids_computed = []
        for line in self:
            if line._origin.id and (
                line.journal_id.statement_line_internal_index
                == "date_statement_id_line_sequence_id"
            ):
                line.internal_index = (
                    f"{line.date.strftime('%Y%m%d')}"
                    f"{line.statement_id.id:0>10}"
                    f"{MAXINT - line.sequence:0>10}"
                    f"{line._origin.id:0>10}"
                )
                line_ids_computed.append(line.id)
        lines_computed = self.env["account.bank.statement.line"].browse(
            line_ids_computed
        )
        return super(
            AccountBankStatementLine, self - lines_computed
        )._compute_internal_index()
