# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import fields, models


class PlaidAccountSelect(models.TransientModel):
    _name = "plaid.account.select"
    _description = "Choose the Plaid account to import"

    provider_id = fields.Many2one(
        comodel_name="online.bank.statement.provider",
        required=True,
        ondelete="cascade",
    )
    line_ids = fields.One2many(
        comodel_name="plaid.account.select.line",
        inverse_name="wizard_id",
    )
    line_id = fields.Many2one(
        comodel_name="plaid.account.select.line",
        string="Account",
        domain="[('wizard_id', '=', id)]",
    )

    def action_select(self):
        self.ensure_one()
        if self.line_id:
            self.provider_id.write(
                {
                    "plaid_account_id": self.line_id.plaid_account_id,
                    "plaid_account_name": self.line_id.name,
                }
            )


class PlaidAccountSelectLine(models.TransientModel):
    _name = "plaid.account.select.line"
    _description = "Plaid account"

    wizard_id = fields.Many2one(
        comodel_name="plaid.account.select",
        required=True,
        ondelete="cascade",
    )
    plaid_account_id = fields.Char(required=True)
    name = fields.Char()
