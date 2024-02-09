# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        res = super()._get_bank_statements_available_import_formats()
        res.append("PayPal Reports")
        return res
