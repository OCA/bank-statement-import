# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class OnlineBankStatementPullWizard(models.TransientModel):
    _name = 'online.bank.statement.pull.wizard'
    _description = 'Online Bank Statement Pull Wizard'

    date_since = fields.Datetime(
        string='Since',
        required=True,
        default=fields.Datetime.now,
    )
    date_until = fields.Datetime(
        string='Until',
        required=True,
        default=fields.Datetime.now,
    )
    provider_ids = fields.Many2many(
        string='Providers',
        comodel_name='online.bank.statement.provider',
        column1='wizard_id',
        column2='provider_id',
        relation='online_bank_statement_provider_pull_wizard_rel',
    )

    @api.multi
    def action_pull(self):
        self.ensure_one()
        self.with_context(
            active_test=False,
        ).provider_ids._pull(
            self.date_since,
            self.date_until
        )
        return {'type': 'ir.actions.act_window_close'}
