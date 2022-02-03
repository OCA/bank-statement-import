# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class ResPartnerBank(models.Model):

    _inherit = "res.partner.bank"

    nordigen_account_id = fields.Char(string="Nordigen Account ID", required=False)
