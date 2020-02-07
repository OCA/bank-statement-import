# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_camt method to account.bank.statement.import."""

    _inherit = "account.bank.statement.import"

    def _create_bank_statements(self, stmts_vals):
        """ Set balance_end_real if not already provided by the file."""

        statement_line_ids, notifications = super()._create_bank_statements(stmts_vals)
        statements = self.env["account.bank.statement"].search(
            [("line_ids", "in", statement_line_ids)]
        )
        for statement in statements:
            if not statement.balance_end_real:
                amount = sum(statement.line_ids.mapped("amount"))
                statement.balance_end_real = statement.balance_start + amount
        return statement_line_ids, notifications

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        """Search partner from partner reference"""
        stmts_vals = super()._complete_stmts_vals(stmts_vals, journal, account_number)
        for st_vals in stmts_vals:
            for line_vals in st_vals["transactions"]:
                if "partner_ref" in line_vals:
                    partner_ref = line_vals.pop("partner_ref")
                    partner = self.env["res.partner"].search(
                        [("ref", "=", partner_ref)], limit=1
                    )
                    line_vals["partner_id"] = partner.id

        return stmts_vals
