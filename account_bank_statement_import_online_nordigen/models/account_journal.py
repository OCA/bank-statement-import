# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountJournal(models.Model):

    _inherit = "account.journal"

    nordigen_institution_id = fields.Char(
        string="Nordigen Institution ID", required=False
    )
