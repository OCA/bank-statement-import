# Copyright 2021 CampToCamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models

MODULE = "account_statement_import_camt"
CHECKING_NAME_UNIQUE = MODULE + ".checking_bank_statement_name_unique"


class ResConfigSetting(models.TransientModel):
    _inherit = "res.config.settings"

    checking_bank_statement_name_unique = fields.Boolean(
        string="Unique bank statement name",
        config_parameter=CHECKING_NAME_UNIQUE,
        default=False,
    )
