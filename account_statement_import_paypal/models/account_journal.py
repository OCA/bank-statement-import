# Copyright 2019 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    paypal_map_id = fields.Many2one(
        comodel_name='account.bank.statement.import.paypal.map',
        string='Paypal Map',
    )
