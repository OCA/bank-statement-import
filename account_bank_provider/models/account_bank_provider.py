# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models, _


class AccountBankProvider(models.Model):
    _name = 'account.bank.provider'
    _description = 'Bank Provider'

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    provider_type = fields.Selection([], 'Provider')
    last_sync = fields.Datetime()

    journal_ids = fields.One2many('account.journal', 'bank_provider_id',
                                  string='Journals', domain=[('type', '=', 'bank')])

    def action_sync_now(self):
        for provider in self.filtered(lambda x: x.provider_type and x.journal_ids):
            getattr(provider, '_sync_%s' % provider.provider_type)()
            provider.sudo().last_sync = fields.Datetime.now()
        self.journal_ids.filtered(
            lambda x: x.bank_statements_source != 'bank_provider').write(
            {'bank_statements_source': 'bank_provider'})

    @api.model
    def _cron_sync(self):
        self.search([]).action_sync_now()
