# Copyright 2021 Therp BV <https://therp.nl>.
# @author: Ronald Portier <ronald@therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class OnlineBankStatementProviderPonto(models.Model):
    _inherit = "online.bank.statement.provider"

    def _ponto_get_transaction_vals(self, transaction, sequence):
        """Remove duplicate information from payment_ref (Label)."""
        self.ensure_one()
        vals_line = super()._ponto_get_transaction_vals(transaction, sequence)
        if not self.journal_id.bank_account_id.bank_id.bic == "INGBNL2A":
            return vals_line
        payment_ref = vals_line["payment_ref"]
        payment_ref_elements = payment_ref.split("<br>")
        keep_elements = []
        for element in payment_ref_elements:
            if element.startswith("Naam"):
                continue
            if element.startswith("Datum"):
                continue
            if element.startswith("Valutadatum"):
                continue
            if element.startswith("IBAN"):
                continue
            element = element.replace("Omschrijving: ", "")  # Remove unneeded tag.
            keep_elements.append(element)
        if keep_elements:
            payment_ref = ", ".join(keep_elements)
        else:
            payment_ref = False
        vals_line["payment_ref"] = payment_ref
        return vals_line
