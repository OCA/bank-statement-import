# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    default_sheet_mapping_id = fields.Many2one(
        comodel_name="account.bank.statement.import.sheet.mapping",
    )

    def _get_bank_statements_available_import_formats(self):
        res = super()._get_bank_statements_available_import_formats()
        res.append("TXT/CSV/XSLX")
        return res
