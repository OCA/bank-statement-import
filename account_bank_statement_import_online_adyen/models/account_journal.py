# Copyright 2021 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def write(self, vals):
        """Do not reset a provider to file_import, if that will delete provider."""
        # TODO: In the future place this in super account_bank_statement_import_online.
        for this in self:
            is_online = this.bank_statements_source == "online"
            if is_online and vals.get("bank_statements_source", "online") != "online":
                vals.pop("bank_statements_source")
            super(AccountJournal, this).write(vals)
        return True

    @api.model
    def _selection_online_bank_statement_provider(self):
        res = super()._selection_online_bank_statement_provider()
        res.append(("dummy_adyen", "Dummy Adyen"))
        return res

    @api.model
    def values_online_bank_statement_provider(self):
        res = super().values_online_bank_statement_provider()
        if self.user_has_groups("base.group_no_one"):
            res += [("dummy_adyen", "Dummy Adyen")]
        return res
