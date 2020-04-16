# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import requests
import json
import dateutil
import pytz
import re

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountBankProvider(models.Model):
    _inherit = 'account.bank.provider'

    provider_type = fields.Selection(selection_add=[('qonto', 'Qonto')])
    provider_qonto_login = fields.Char('Qonto Login')
    provider_qonto_key = fields.Char('Qonto Secret Key')
    provider_qonto_endpoint = fields.Char('Qonto End Point', default='https://thirdparty.qonto.eu/v2')

    def _qonto_header(self):
        self.ensure_one()
        if self.provider_qonto_login and self.provider_qonto_key:
            return {'Authorization': '%s:%s' % (self.provider_qonto_login, self.provider_qonto_key)}
        raise UserError(_('Please fill login and key'))

    def _get_qonto_slug(self):
        self.ensure_one()
        url = self.provider_qonto_endpoint + '/organizations/%7Bid%7D'
        response = requests.get(url, verify=False, headers=self._qonto_header())
        if response.status_code == 200:
            data = json.loads(response.text)
            res = {}
            for account in data.get('organization', {}).get('bank_accounts', []):
                iban = sanitize_account_number(account.get('iban', ''))
                res[iban] = account.get('slug')
            return res
        raise UserError(_('%s \n\n %s') % (response.status_code, response.text))

    def _get_qonto_transaction(self, journal, slug):
        self.ensure_one()
        last_date = journal.bank_provider_last_transaction_date
        iban = sanitize_account_number(journal.bank_account_id.acc_number)
        url = self.provider_qonto_endpoint + '/transactions'
        params = {'slug': slug, 'iban': iban}
        if last_date:
            params['settled_at_from'] = last_date.replace(microsecond=0).isoformat() + 'Z'
        response = requests.get(url, verify=False, params=params, headers=self._qonto_header())
        if response.status_code == 200:
            return json.loads(response.text)
        raise UserError(_('%s \n\n %s') % (response.status_code, response.text))

    def _sync_qonto(self):
        self.ensure_one()
        BankStatementLine = self.env['account.bank.statement.line']
        BankStatement = self.env['account.bank.statement']

        slugs = self._get_qonto_slug()

        for journal in self.journal_ids:
            slug = slugs.get(sanitize_account_number(journal.bank_account_id.acc_number))
            if not slug:
                raise UserError(
                    _('Qonto : wrong configuration, unknow account %s') % journal.bank_account_id.acc_number)

            data = self._get_qonto_transaction(journal, slug)

            currency = journal.currency_id or journal.company_id.currency_id

            new_transaction = []
            sequence = 0
            for transaction in data.get('transactions', []):
                if BankStatementLine.sudo().search(
                        [('unique_import_id', '=', transaction['transaction_id']),
                         ('journal_id', '=', journal.id)], limit=1):
                    continue
                date = dateutil.parser.isoparse(transaction['settled_at'])
                date = fields.Date.to_date(date.astimezone(pytz.timezone('Europe/Paris')))
                side = 1 if transaction['side'] == 'credit' else -1
                sequence += 1
                vals_line = {
                    'sequence': sequence,
                    'date': date,
                    'name': re.sub(' +', ' ', '%s %s' % (transaction['label'], transaction['reference'])) or '/',
                    'ref': transaction['reference'],
                    'unique_import_id': transaction['transaction_id'],
                    'amount': transaction['amount'] * side,
                }

                line_currency = self.env['res.currency'].search(
                    [('name', '=', transaction['local_currency'])], limit=1)

                if currency != line_currency:
                    vals_line.update({'currency_id': currency.id,
                                      'amount_currency': transaction['local_amount'] * side})

                new_transaction.append(vals_line)
            if new_transaction:
                date = max([t['date'] for t in new_transaction])
                start_balance = BankStatement.search([('journal_id', '=', journal.id)],
                                                     order='date desc, id desc').balance_end_real or 0
                end_balance = sum([t['amount'] for t in new_transaction]) + start_balance
                vals = {'name': 'qonto Sync',
                        'journal_id': journal.id,
                        'date': date,
                        'balance_start': start_balance,
                        'balance_end_real': end_balance,
                        'line_ids': [(0, 0, t) for t in new_transaction]}
                BankStatement.sudo().create(vals)
                journal.bank_provider_last_transaction_date = date
