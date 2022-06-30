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
        """Find partner by searching invoice with reference or so name."""
        if transaction.get("partner_id", False):
            return
        invoice_model = self.env["account.move"]
        sale_order_model = self.env["sale.order"]
        invoice = None
        transaction_keys = ["ref", "name"]
        invoice_fields = ["invoice_origin", "ref", "name"]
        sale_order_fields = ["client_order_ref", "name"]
        for key in transaction_keys:
            value = transaction.get(key, False)
            if not value:
                continue
            for fieldname in invoice_fields:
                invoice = invoice_model.search([(fieldname, "=", value)], limit=1)
                if invoice:
                    # We need a partner of type contact here because of reconciliation.
                    # Lines cannot be reconciled if partner is an address
                    partner = self._get_effective_partner(invoice.partner_id)
                    transaction["partner_id"] = partner.id
                    return
            for fieldname in sale_order_fields:
                sale_order = sale_order_model.search([(fieldname, "=", value)], limit=1)
                if sale_order:
                    partner = self._get_effective_partner(sale_order.partner_id)
                    transaction["partner_id"] = partner.id
                    return

    def _get_effective_partner(self, partner):
        """Find contact partner for invoice, sale order"""
        if partner.type == "contact":
            return partner
        if partner.parent_id.type == "contact":
            return partner.parent_id
        # If there's no contact,
        # return original partner
        return partner
