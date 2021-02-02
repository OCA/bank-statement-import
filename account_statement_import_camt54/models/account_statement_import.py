# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    """Add process_camt method to account.bank.statement.import."""

    _inherit = "account.statement.import"

    def _create_bank_statements(self, stmts_vals, result):
        """Create additional line in statement to set bank statement statement
        to 0 balance"""

        super()._create_bank_statements(stmts_vals, result)
        statements = self.env["account.bank.statement"].browse(result["statement_ids"])
        for statement in statements:
            amount = sum(statement.line_ids.mapped("amount"))
            if statement.journal_id.transfer_line:
                if amount != 0:
                    amount = -amount
                statement.line_ids.create(
                    {
                        "amount": amount,
                        "statement_id": statement.id,
                        "date": statement.date,
                        "payment_ref": statement.name,
                    }
                )
                statement.balance_end_real = statement.balance_start
            else:
                statement.balance_end_real = statement.balance_start + amount

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
