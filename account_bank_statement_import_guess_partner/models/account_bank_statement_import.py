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
        invoice_model = self.env["account.move"]
        invoice = None
        transaction_keys = ["ref", "name"]
        invoice_fields = ["invoice_origin", "ref", "name"]
        for key in transaction_keys:
            value = transaction.get(key, False)
            if not value:
                continue
            for fieldname in invoice_fields:
                invoice = invoice_model.search([(fieldname, "=", value)], limit=1)
                if invoice:
                    transaction["partner_id"] = invoice.partner_id.id
                    return
