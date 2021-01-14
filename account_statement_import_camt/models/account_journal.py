# Copyright 2019 ACSONE SA/NV <thomas.binsfeld@acsone.eu>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        res = super(
            AccountJournal, self
        )._get_bank_statements_available_import_formats()
        res.extend([_("camt.053.001.02"), _("camt.054.001.02")])
        return res
