# Copyright 2017 Opener BV (<https://opener.amsterdam>)
# Copyright 2020 Vanmoof BV (<https://www.vanmoof.com>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    adyen_merchant_account = fields.Char(
        help=(
            "Fill in the exact merchant account string to select this "
            "journal when importing Adyen statements"
        )
    )

    def _get_bank_statements_available_import_formats(self):
        res = super()._get_bank_statements_available_import_formats()
        res.append("adyen")
        return res
