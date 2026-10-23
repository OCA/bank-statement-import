# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models
from odoo.exceptions import ValidationError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _update_vals(self, vals):
        res = super()._update_vals(vals)
        # The transactions carry no reliable unique id: generate one, so that
        # pulling an overlapping period does not duplicate the lines
        if vals.get("online_bank_statement_provider") == "fints":
            vals["generate_unique_import_id"] = True
        return res

    @api.constrains("generate_unique_import_id", "online_bank_statement_provider")
    def _check_fints_generate_unique_import_id(self):
        for journal in self:
            if (
                journal.online_bank_statement_provider == "fints"
                and not journal.generate_unique_import_id
            ):
                raise ValidationError(
                    self.env._(
                        "Journal %s pulls its statements via FinTS, "
                        "'Generate Missing Import IDs' must stay enabled.",
                        journal.display_name,
                    )
                )
