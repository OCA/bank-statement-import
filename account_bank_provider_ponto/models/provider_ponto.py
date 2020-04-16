# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import requests
import json
import base64
import time
import pytz
import re
import dateutil

from odoo import api, fields, models, _
from odoo.exceptions import UserError
from dateutil.relativedelta import relativedelta
from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountBankProvider(models.Model):
    _inherit = 'account.bank.provider'

    provider_type = fields.Selection(selection_add=[('ponto', 'ponto')])
    provider_ponto_cliend_id = fields.Char('Ponto Login')
    provider_ponto_key = fields.Char('Ponto Secret Key')
    provider_ponto_endpoint = fields.Char('Ponto End Point', default='https://api.myponto.com')
    provider_ponto_token = fields.Char(readonly=True)
    provider_ponto_token_expiration = fields.Datetime(readonly=True)

    def _ponto_header_token(self):
        self.ensure_one()
        if self.provider_ponto_cliend_id and self.provider_ponto_key:
            login = '%s:%s' % (self.provider_ponto_cliend_id, self.provider_ponto_key)
            login = base64.b64encode(login.encode('UTF-8')).decode('UTF-8')
            return {'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json',
                    'Authorization': 'Basic %s' % login, }
        raise UserError(_('Please fill login and key'))

    def _ponto_header(self):
        self.ensure_one()
        if not self.provider_ponto_token or not self.provider_ponto_token_expiration \
                or self.provider_ponto_token_expiration <= fields.Datetime.now():
            url = self.provider_ponto_endpoint + '/oauth2/token'
            response = requests.post(url, verify=False,
                                     params={'grant_type': 'client_credentials'},
                                     headers=self._ponto_header_token())
            if response.status_code == 200:
                data = json.loads(response.text)
                access_token = data.get('access_token', False)
                if not access_token:
                    raise UserError(_('Ponto : no token'))
                else:
                    self.provider_ponto_token = access_token
                    self.provider_ponto_token_expiration = fields.Datetime.now() + relativedelta(
                        seconds=data.get('expires_in', False))
            else:
                raise UserError(_('%s \n\n %s') % (response.status_code, response.text))
        return {'Accept': 'application/json',
                'Authorization': 'Bearer %s' % self.provider_ponto_token, }

    def _get_ponto_account_ids(self):
        url = self.provider_ponto_endpoint + '/accounts'
        response = requests.get(url, verify=False, params={'limit': 100}, headers=self._ponto_header())
        if response.status_code == 200:
            data = json.loads(response.text)
            res = {}
            for account in data.get('data', []):
                iban = sanitize_account_number(account.get('attributes', {}).get('reference', ''))
                res[iban] = account.get('id')
            return res
        raise UserError(_('%s \n\n %s') % (response.status_code, response.text))

    def _ponto_synchronisation(self, account_id):
        url = self.provider_ponto_endpoint + '/synchronizations'
        data = {'data': {
            'type': 'synchronization',
            'attributes': {
                'resourceType': 'account',
                'resourceId': account_id,
                'subtype': 'accountTransactions'
            }
        }}
        response = requests.post(url, verify=False, headers=self._ponto_header(), json=data)
        if response.status_code in (200, 201, 400):
            data = json.loads(response.text)
            sync_id = data.get('attributes', {}).get('resourceId', False)
        else:
            raise UserError(_('Error during Create Synchronisation %s \n\n %s') % (response.status_code, response.text))

        # Check synchronisation
        if not sync_id:
            return
        url = self.provider_ponto_endpoint + '/synchronizations/' + sync_id
        number = 0
        while number == 100:
            number += 1
            response = requests.get(url, verify=False, headers=self._ponto_header())
            if response.status_code == 200:
                data = json.loads(response.text)
                status = data.get('status', {})
                if status in ('success', 'error'):
                    return
            time.sleep(4)

    def _get_ponto_transaction(self, journal, account_id):
        last_identifier = journal.bank_provider_last_transaction_identifier
        url = self.provider_ponto_endpoint + '/accounts/' + account_id + '/transactions'
        params = {'limit': 100}
        page_next = True
        if last_identifier:
            params['before'] = last_identifier
            page_next = False
        transaction_lines = []
        last_identifier = False
        while url:
            response = requests.get(url, verify=False, params=params, headers=self._ponto_header())
            if response.status_code == 200:
                if params.get('before'):
                    params.pop('before')
                data = json.loads(response.text)
                links = data.get('links', {})
                if page_next:
                    url = links.get('next', False)
                else:
                    url = links.get('prev', False)
                transactions = data.get('data', [])
                if transactions:
                    transaction_lines.extend(transactions)
                    last_identifier = transactions[0].get('id')
            else:
                raise UserError(
                    _('Error during get transaction.\n\n%s \n\n %s') % (response.status_code, response.text))
        if last_identifier:
            journal.bank_provider_last_transaction_identifier = last_identifier
        return transaction_lines

    def _sync_ponto(self):
        self.ensure_one()
        StatementLine = self.env['account.bank.statement.line']
        Statement = self.env['account.bank.statement']

        account_ids = self._get_ponto_account_ids()

        for journal in self.journal_ids:
            iban = sanitize_account_number(journal.bank_account_id.acc_number)
            account_id = account_ids.get(iban)
            if not account_id:
                raise UserError(
                    _('ponto : wrong configuration, unknow account %s') % journal.bank_account_id.acc_number)

            self._ponto_synchronisation(account_id)

            transaction_lines = self._get_ponto_transaction(journal, account_id)
            new_transactions = []
            sequence = 0
            for transaction in transaction_lines:
                if StatementLine.sudo().search(
                        [('unique_import_id', '=', transaction['id']),
                         ('journal_id', '=', journal.id)], limit=1):
                    continue

                sequence += 1
                ref = '%s %s' % (attributes.get('description'), attributes.get('counterpartName'))
                attributes = transaction.get('attributes', {})
                date = dateutil.parser.isoparse(attributes.get('executionDate'))
                date = fields.Date.to_date(date.astimezone(pytz.timezone('Europe/Paris')))

                vals_line = {
                    'sequence': sequence,
                    'date': date,
                    'name': re.sub(' +', ' ', ref) or '/',
                    'ref': attributes.get('remittanceInformation', ''),
                    'unique_import_id': transaction['id'],
                    'amount': attributes['amount'],
                }
                new_transactions.append(vals_line)

            if new_transactions:
                date = max([t['date'] for t in new_transactions])
                start_balance = Statement.search([('journal_id', '=', journal.id)],
                                                 order='date desc, id desc').balance_end_real or 0
                end_balance = sum([t['amount'] for t in new_transactions]) + start_balance
                vals = {'name': 'Ponto Sync',
                        'journal_id': journal.id,
                        'date': date,
                        'balance_start': start_balance,
                        'balance_end_real': end_balance,
                        'line_ids': [(0, 0, t) for t in new_transactions]}

                Statement.sudo().create(vals)
                journal.bank_provider_last_transaction_date = date
