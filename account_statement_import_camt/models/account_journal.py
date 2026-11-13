# Copyright 2019 ACSONE SA/NV <thomas.binsfeld@acsone.eu>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        res = super()._get_bank_statements_available_import_formats()
        res.extend(
            [
                self.env._("camt.053.001.02"),
                self.env._("camt.054.001.02"),
            ]
        )
        return res
