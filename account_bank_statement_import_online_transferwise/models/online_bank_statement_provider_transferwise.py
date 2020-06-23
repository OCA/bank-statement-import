# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from dateutil.relativedelta import relativedelta
import dateutil.parser
from decimal import Decimal
import itertools
import json
import pytz
import urllib.parse
import urllib.request

from odoo import models, api, _
from odoo.exceptions import UserError

TRANSFERWISE_API_BASE = 'https://api.transferwise.com'


class OnlineBankStatementProviderTransferwise(models.Model):
    _inherit = 'online.bank.statement.provider'

    @api.model
    def values_transferwise_profile(self):
        api_base = self.env.context.get('api_base') or TRANSFERWISE_API_BASE
        api_key = self.env.context.get('api_key')
        if not api_key:
            return []
        try:
            url = api_base + '/v1/profiles'
            data = self._transferwise_retrieve(url, api_key)
        except:
            return []
        return list(map(
            lambda entry: (
                str(entry['id']),
                '%s %s (personal)' % (
                    entry['details']['firstName'],
                    entry['details']['lastName'],
                )
                if entry['type'] == 'personal'
                else entry['details']['name']
            ),
            data
        ))

    @api.model
    def _get_available_services(self):
        return super(OnlineBankStatementProviderTransferwise, self) \
            ._get_available_services() + [('transferwise', 'TransferWise.com')]

    @api.multi
    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != 'transferwise':
            return super(
                OnlineBankStatementProviderTransferwise, self
            )._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        api_base = self.api_base or TRANSFERWISE_API_BASE
        api_key = self.password
        currency = (
            self.currency_id or self.company_id.currency_id
        ).name

        if date_since.tzinfo:
            date_since = date_since.astimezone(pytz.utc).replace(tzinfo=None)
        if date_until.tzinfo:
            date_until = date_until.astimezone(pytz.utc).replace(tzinfo=None)

        # Get corresponding balance by currency
        url = api_base + '/v1/borderless-accounts?profileId=%s' % (
            self.origin,
        )
        data = self._transferwise_retrieve(url, api_key)
        borderless_account = data[0]['id']
        balance = list(filter(
            lambda balance: balance['currency'] == currency,
            data[0]['balances']
        ))
        if not balance:
            return None

        # Notes on /statement endpoint:
        #  - intervalStart <= date < intervalEnd

        # Get starting balance
        starting_balance_timestamp = date_since.isoformat() + 'Z'
        url = api_base + (
            '/v1/borderless-accounts/%s/statement.json' +
            '?currency=%s&intervalStart=%s&intervalEnd=%s'
        ) % (
            borderless_account,
            currency,
            starting_balance_timestamp,
            starting_balance_timestamp,
        )
        data = self._transferwise_retrieve(url, api_key)
        balance_start = data['endOfStatementBalance']['value']

        # Get statements, using 469 days (around 1 year 3 month) as step.
        interval_step = relativedelta(days=469)
        interval_start = date_since
        interval_end = date_until
        transactions = []
        balance_end = None
        while interval_start < interval_end:
            url = api_base + (
                '/v1/borderless-accounts/%s/statement.json' +
                '?currency=%s&intervalStart=%s&intervalEnd=%s'
            ) % (
                borderless_account,
                currency,
                interval_start.isoformat() + 'Z',
                min(
                    interval_start + interval_step, interval_end
                ).isoformat() + 'Z',
            )
            data = self._transferwise_retrieve(url, api_key)
            transactions += data['transactions']
            balance_end = data['endOfStatementBalance']['value']
            interval_start += interval_step
        if balance_end is None:
            raise UserError(_('Ending balance unavailable'))

        # Normalize transactions' date, sort by it, and get lines
        transactions = map(
            lambda transaction: self._transferwise_preparse_transaction(
                transaction
            ),
            transactions
        )
        lines = list(itertools.chain.from_iterable(map(
            lambda x: self._transferwise_transaction_to_lines(x),
            sorted(
                transactions,
                key=lambda transaction: transaction['date']
            )
        )))

        return lines, {
            'balance_start': balance_start,
            'balance_end_real': balance_end,
        }

    @api.model
    def _transferwise_preparse_transaction(self, transaction):
        transaction['date'] = dateutil.parser.parse(
            transaction['date']
        ).replace(tzinfo=None)
        return transaction

    @api.model
    def _transferwise_transaction_to_lines(self, transaction):
        reference_number = transaction['referenceNumber']
        details = transaction.get('details', {})
        exchange_details = transaction.get('exchangeDetails')
        recipient = details.get('recipient')
        total_fees = transaction.get('totalFees')
        date = transaction['date']
        payment_reference = details.get('paymentReference')
        description = details.get('description')
        note = reference_number
        if description:
            note = '%s: %s' % (
                note,
                description
            )
        amount = transaction['amount']
        amount_value = amount.get('value', 0)
        fees_value = total_fees.get('value', Decimal()).copy_abs()
        if amount_value.is_signed():
            fees_value = fees_value.copy_negate()
        amount_value -= fees_value
        unique_import_id = '%s-%s-%s' % (
            transaction['type'],
            reference_number,
            int(date.timestamp()),
        )
        line = {
            'name': payment_reference or description or '',
            'amount': str(amount_value),
            'date': date,
            'note': note,
            'unique_import_id': unique_import_id,
        }
        if recipient:
            if 'name' in recipient:
                line.update({
                    'partner_name': recipient['name'],
                })
            if 'bankAccount' in recipient:
                line.update({
                    'account_number': recipient['bankAccount'],
                })
        elif 'merchant' in details:
            merchant = details['merchant']
            if 'name' in merchant:
                line.update({
                    'partner_name': merchant['name'],
                })
        else:
            if 'senderName' in details:
                line.update({
                    'partner_name': details['senderName'],
                })
            if 'senderAccount' in details:
                line.update({
                    'account_number': details['senderAccount'],
                })
        if exchange_details:
            to_amount = exchange_details['toAmount']
            from_amount = exchange_details['fromAmount']
            other_amount_value = (
                to_amount['value']
                if to_amount['currency'] != amount['currency']
                else from_amount['value']
            )
            other_currency_name = (
                to_amount['currency']
                if to_amount['currency'] != amount['currency']
                else from_amount['currency']
            )
            other_amount_value = other_amount_value.copy_abs()
            if amount_value.is_signed():
                other_amount_value = other_amount_value.copy_negate()
            other_currency = self.env['res.currency'].search(
                [('name', '=', other_currency_name)],
                limit=1
            )
            if other_amount_value and other_currency:
                line.update({
                    'amount_currency': str(other_amount_value),
                    'currency_id': other_currency.id,
                })
        lines = [line]
        if fees_value:
            lines += [{
                'name': _('Fee for %s') % reference_number,
                'amount': str(fees_value),
                'date': date,
                'partner_name': 'TransferWise',
                'unique_import_id': '%s-FEE' % unique_import_id,
                'note': _('Transaction fee for %s') % reference_number,
            }]
        return lines

    @api.model
    def _transferwise_validate(self, content):
        content = json.loads(content, parse_float=Decimal)
        if 'error' in content and content['error']:
            raise UserError(
                content['error_description']
                if 'error_description' in content
                else 'Unknown error'
            )
        return content

    @api.model
    def _transferwise_retrieve(self, url, api_key):
        with self._transferwise_urlopen(url, api_key) as response:
            content = response.read().decode(
                response.headers.get_content_charset()
            )
        return self._transferwise_validate(content)

    @api.model
    def _transferwise_urlopen(self, url, api_key):
        if not api_key:
            raise UserError(_('No API key specified!'))
        request = urllib.request.Request(url)
        request.add_header(
            'Authorization',
            'Bearer %s' % api_key
        )
        return urllib.request.urlopen(request)
