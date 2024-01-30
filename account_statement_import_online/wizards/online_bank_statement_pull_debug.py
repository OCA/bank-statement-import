# Copyright 2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OnlineBankStatementPullWizard(models.TransientModel):
    _name = "online.bank.statement.pull.debug"
    _description = "Online Bank Statement Pull Debug Wizard"

    data = fields.Text(string="RAW data", required=True, readonly=True)
