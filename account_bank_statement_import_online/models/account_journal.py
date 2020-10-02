# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models, fields, api, _

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    online_bank_statement_provider = fields.Selection(
        selection=lambda self: self.env[
            'account.journal'
        ]._selection_online_bank_statement_provider(),
    )
    online_bank_statement_provider_id = fields.Many2one(
        string='Statement Provider',
        comodel_name='online.bank.statement.provider',
        ondelete='restrict',
        copy=False,
    )

    def __get_bank_statements_available_sources(self):
        result = super().__get_bank_statements_available_sources()
        result.append(('online', _('Online (OCA)')))
        return result

    @api.model
    def _selection_online_bank_statement_provider(self):
        return self.env[
            'online.bank.statement.provider'
        ]._get_available_services() + [('dummy', 'Dummy')]

    @api.model
    def values_online_bank_statement_provider(self):
        res = self.env[
            'online.bank.statement.provider'
        ]._get_available_services()
        if self.user_has_groups('base.group_no_one'):
            res += [('dummy', 'Dummy')]
        return res

    @api.multi
    def _update_online_bank_statement_provider_id(self):
        OnlineBankStatementProvider = (
            self.env['online.bank.statement.provider']
        )
        for journal in self.filtered('id'):
            provider_id = journal.online_bank_statement_provider_id
            if journal.bank_statements_source != 'online':
                journal.online_bank_statement_provider_id = False
                if provider_id:
                    provider_id.unlink()
                continue
            if provider_id.service == journal.online_bank_statement_provider:
                continue
            journal.online_bank_statement_provider_id = False
            if provider_id:
                provider_id.unlink()
            journal.online_bank_statement_provider_id = (
                OnlineBankStatementProvider.create({
                    'journal_id': journal.id,
                    'service': journal.online_bank_statement_provider,
                })
            )

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if 'bank_statements_source' in vals \
                or 'online_bank_statement_provider' in vals:
            rec._update_online_bank_statement_provider_id()
        return rec

    @api.multi
    def write(self, vals):
        res = super().write(vals)
        if 'bank_statements_source' in vals \
                or 'online_bank_statement_provider' in vals:
            self._update_online_bank_statement_provider_id()
        return res

    @api.multi
    def action_online_bank_statements_pull_wizard(self):
        provider_ids = self.mapped('online_bank_statement_provider_id').ids
        return {
            'name': _('Online Bank Statement Pull Wizard'),
            'type': 'ir.actions.act_window',
            'res_model': 'online.bank.statement.pull.wizard',
            'views': [[False, 'form']],
            'target': 'new',
            'context': {
                'default_provider_ids': [(6, False, provider_ids)],
                'active_test': False,
            },
        }
