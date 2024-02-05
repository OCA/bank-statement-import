# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import api, models

from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _statement_line_import_speeddict(self):
        """This method is designed to be inherited by reconciliation modules.
        These modules can take advantage of this method to pre-fetch data
        that will later be used for many statement lines (to avoid
        searching data for each statement line).
        The goal is to improve performances.
        """
        self.ensure_one()
        speeddict = {"account_number": {}}
        partner_banks = self.env["res.partner.bank"].search_read(
            [("company_id", "in", (False, self.company_id.id))],
            ["acc_number", "partner_id"],
        )
        for partner_bank in partner_banks:
            speeddict["account_number"][partner_bank["acc_number"]] = {
                "partner_id": partner_bank["partner_id"][0],
                "partner_bank_id": partner_bank["id"],
            }
        return speeddict

    def _statement_line_import_update_hook(self, st_line_vals, speeddict):
        """This method is designed to be inherited by reconciliation modules.
        In this method you can:
        - update the partner of the line by writing st_line_vals['partner_id']
        - set an automated counter-part via counterpart_account_id by writing
          st_line_vals['counterpart_account_id']
        - do anythink you want with the statement line
        """
        self.ensure_one()
        if st_line_vals.get("account_number"):
            st_line_vals["account_number"] = self._sanitize_bank_account_number(
                st_line_vals["account_number"]
            )
            if not st_line_vals.get("partner_id") and speeddict["account_number"].get(
                st_line_vals["account_number"]
            ):
                st_line_vals.update(
                    speeddict["account_number"][st_line_vals["account_number"]]
                )

    def _statement_line_import_update_unique_import_id(
        self, st_line_vals, account_number
    ):
        self.ensure_one()
        if st_line_vals.get("unique_import_id"):
            sanitized_acc_number = self._sanitize_bank_account_number(account_number)
            st_line_vals["unique_import_id"] = (
                (sanitized_acc_number and sanitized_acc_number + "-" or "")
                + str(self.id)
                + "-"
                + st_line_vals["unique_import_id"]
            )

    @api.model
    def _sanitize_bank_account_number(self, account_number):
        """Hook for extension"""
        return sanitize_account_number(account_number)
