# Copyright 2026 Akretion (https://www.akretion.com).
# @author Renato Lima <renato.lima@akretion.com.br>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models

from ..tools import extract_vat_candidates, normalize_vat


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _statement_line_import_speeddict(self):
        speeddict = super()._statement_line_import_speeddict()
        speeddict["vat"] = self._statement_line_import_vat_speeddict()
        return speeddict

    def _statement_line_import_vat_speeddict(self):
        """Return {normalized VAT: {'partner_id': ID}}, pre-fetched once per
        file so that matching a line stays a dict lookup."""
        self.ensure_one()
        res = {}
        # The label of a line often repeats the VAT of the company itself
        # (bank fees, transfers between own accounts). Matching it would set
        # the company as the partner of the line, which is never wanted.
        own_commercial_partner = self.company_id.partner_id.commercial_partner_id
        partners = self.env["res.partner"].search_read(
            [
                ("vat", "!=", False),
                ("company_id", "in", (False, self.company_id.id)),
                ("commercial_partner_id", "!=", own_commercial_partner.id),
            ],
            ["vat", "parent_id"],
        )
        for partner in partners:
            vat = normalize_vat(partner["vat"])
            if not vat:
                continue
            # Several contacts can share the same VAT (a company and its child
            # contacts), in which case we keep the top-level one.
            if vat in res and partner["parent_id"]:
                continue
            res[vat] = {"partner_id": partner["id"]}
        return res

    def _statement_line_import_update_hook(self, st_line_vals, speeddict):
        res = super()._statement_line_import_update_hook(st_line_vals, speeddict)
        if not st_line_vals.get("partner_id"):
            self._statement_line_import_match_partner_by_vat(st_line_vals, speeddict)
        return res

    def _statement_line_import_vat_match_fields(self):
        """Keys of the statement line values scanned for a VAT number, most
        specific first. Hook for extension."""
        return ("partner_name", "payment_ref", "ref", "narration")

    def _statement_line_import_match_partner_by_vat(self, st_line_vals, speeddict):
        """Set the partner of the line from a VAT number written in its label.

        Formats such as OFX carry no counterpart account number, so the
        matching of ``account_statement_import_base`` never triggers on them.
        Brazilian banks do write the CNPJ/CPF of the counterpart in the label,
        which this uses instead.
        """
        self.ensure_one()
        vat_speeddict = speeddict.get("vat") or {}
        if not vat_speeddict:
            return False
        for key in self._statement_line_import_vat_match_fields():
            value = st_line_vals.get(key)
            if not value or not isinstance(value, str):
                continue
            for vat in extract_vat_candidates(value):
                match = vat_speeddict.get(vat)
                if match:
                    st_line_vals.update(match)
                    return True
        return False
