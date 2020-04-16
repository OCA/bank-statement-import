# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    def __get_bank_statements_available_sources(self):
        res = super(AccountJournal, self).__get_bank_statements_available_sources()
        res.append(('bank_provider', 'Bank Provider'))
        return res

    bank_provider_id = fields.Many2one('account.bank.provider', string='Bank Provider',
                                       groups='account.group_account_user')
    bank_provider_last_transaction_date = fields.Datetime('Last Transaction', readonly=True,
                                                          groups='account.group_account_user')
    bank_provider_last_transaction_identifier = fields.Char('Last Identifier', readonly=True,
                                                                groups='account.group_account_user')

    def action_bank_provider_sync_now(self):
        self.bank_provider_id.action_sync_now()
