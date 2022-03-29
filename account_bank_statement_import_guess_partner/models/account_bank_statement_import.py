# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Try to determine partner from ref in transaction and from invoice."""
from odoo import models


class AccountBankStatementImport(models.TransientModel):
    """Try to determine partner from ref in transaction and from invoice."""

    _inherit = "account.bank.statement.import"

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        """Try to find partner for each transaction."""
        stmts_vals = super()._complete_stmts_vals(stmts_vals, journal, account_number)
        # Loop over statements.
        for statement in stmts_vals:
            # Loop over transactions in statement.
            for transaction in statement["transactions"]:
                self._complete_transaction(transaction)
        return stmts_vals

    def _complete_transaction(self, transaction):
        """Try to find partner by searching invoice with reference."""
        if transaction.get("partner_id", False):
            return
        if not transaction.get("ref", False):
            return
        ref = transaction["ref"]
        invoice_model = self.env["account.move"]
        # We search each possibility in a separate statement, to prioritize
        # invoice_origin over ref, and ref over name.
        invoice = invoice_model.search([("invoice_origin", "=", ref)], limit=1)
        if not invoice:
            invoice = invoice_model.search([("ref", "=", ref)], limit=1)
            if not invoice:
                invoice = invoice_model.search([("name", "=", ref)], limit=1)
        if invoice:
            transaction["partner_id"] = invoice.partner_id.id
