# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models, _

from datetime import datetime
from decimal import Decimal
from io import StringIO
from os import path
import itertools
from pytz import timezone, utc

import logging
_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = 'account.bank.statement.import.paypal.parser'
    _description = 'Account Bank Statement Import PayPal Parser'

    @api.model
    def parse_header(self, data_file):
        data = StringIO(data_file.decode('utf-8-sig'))
        csv_data = reader(data)
        return list(next(csv_data))

    @api.model
    def parse(self, mapping, data_file, filename):
        journal = self.env['account.journal'].browse(
            self.env.context.get('journal_id')
        )
        currency_code = (
            journal.currency_id or journal.company_id.currency_id
        ).name
        account_number = journal.bank_account_id.acc_number

        name = _('%s: %s') % (
            journal.code,
            path.basename(filename),
        )
        lines = self._parse_lines(mapping, data_file, currency_code)
        if not lines:
            return currency_code, account_number, [{
                'name': name,
                'transactions': [],
            }]

        lines = list(sorted(
            lines,
            key=lambda line: line['timestamp']
        ))
        first_line = lines[0]
        balance_start = first_line['balance_amount']
        balance_start -= first_line['gross_amount']
        balance_start -= first_line['fee_amount']
        last_line = lines[-1]
        balance_end = last_line['balance_amount']

        transactions = list(itertools.chain.from_iterable(map(
            lambda line: self._convert_line_to_transactions(line),
            lines
        )))

        return currency_code, account_number, [{
            'name': name,
            'date': first_line['timestamp'].date(),
            'balance_start': float(balance_start),
            'balance_end_real': float(balance_end),
            'transactions': transactions,
        }]

    def _parse_lines(self, mapping, data_file, currency_code):
        data = StringIO(data_file.decode('utf-8-sig'))
        csv_data = reader(data)

        header = list(next(csv_data))
        date_column = header.index(mapping.date_column)
        time_column = header.index(mapping.time_column)
        tz_column = header.index(mapping.tz_column)
        name_column = header.index(mapping.name_column)
        currency_column = header.index(mapping.currency_column)
        gross_column = header.index(mapping.gross_column)
        fee_column = header.index(mapping.fee_column)
        balance_column = header.index(mapping.balance_column)
        transaction_id_column = header.index(mapping.transaction_id_column)
        try:
            description_column = header.index(mapping.description_column)
        except ValueError:
            description_column = None
        try:
            type_column = header.index(mapping.type_column)
        except ValueError:
            type_column = None
        try:
            from_email_address_column = header.index(
                mapping.from_email_address_column
            )
        except ValueError:
            from_email_address_column = None
        try:
            to_email_address_column = header.index(
                mapping.to_email_address_column
            )
        except ValueError:
            to_email_address_column = None
        try:
            invoice_id_column = header.index(mapping.invoice_id_column)
        except ValueError:
            invoice_id_column = None
        try:
            subject_column = header.index(mapping.subject_column)
        except ValueError:
            subject_column = None
        try:
            note_column = header.index(mapping.note_column)
        except ValueError:
            note_column = None
        try:
            bank_name_column = header.index(mapping.bank_name_column)
        except ValueError:
            bank_name_column = None
        try:
            bank_account_column = header.index(mapping.bank_account_column)
        except ValueError:
            bank_account_column = None

        lines = []
        for row in csv_data:
            row = list(row)
            date_value = row[date_column]
            time_value = row[time_column]
            tz_value = row[tz_column]
            name_value = row[name_column]
            currency_value = row[currency_column]
            gross_value = row[gross_column]
            fee_value = row[fee_column]
            balance_value = row[balance_column]
            transaction_id_value = row[transaction_id_column]
            description_value = row[description_column] \
                if description_column is not None else None
            type_value = row[type_column] \
                if type_column is not None else None
            from_email_address_value = row[from_email_address_column] \
                if from_email_address_column is not None else None
            to_email_address_value = row[to_email_address_column] \
                if to_email_address_column is not None else None
            invoice_id_value = row[invoice_id_column] \
                if invoice_id_column is not None else None
            subject_value = row[subject_column] \
                if subject_column is not None else None
            note_value = row[note_column] \
                if note_column is not None else None
            bank_name_value = row[bank_name_column] \
                if bank_name_column is not None else None
            bank_account_value = row[bank_account_column] \
                if bank_account_column is not None else None

            if currency_value != currency_code:
                continue

            date = datetime.strptime(date_value, mapping.date_format).date()
            time = datetime.strptime(time_value, mapping.time_format).time()
            timestamp = datetime.combine(date, time)
            tz_value = self._normalize_tz(tz_value)
            tz = timezone(tz_value)
            timestamp = timestamp.replace(tzinfo=tz)
            timestamp = timestamp.astimezone(utc).replace(tzinfo=None)
            gross_amount = self._parse_decimal(gross_value, mapping)
            fee_amount = self._parse_decimal(fee_value, mapping)
            balance_amount = self._parse_decimal(balance_value, mapping)
            bank = '%s - %s' % (
                bank_name_value,
                bank_account_value,
            ) if bank_name_value and bank_account_value else None
            if to_email_address_column is None:
                payer_email = from_email_address_value
            else:
                payer_email = to_email_address_value \
                    if gross_amount < 0.0 else from_email_address_value

            lines.append({
                'transaction_id': transaction_id_value,
                'invoice': invoice_id_value,
                'description': description_value or type_value,
                'details': subject_value or note_value or bank,
                'timestamp': timestamp,
                'gross_amount': gross_amount,
                'fee_amount': fee_amount,
                'balance_amount': balance_amount,
                'payer_name': name_value,
                'payer_email': payer_email,
                'partner_bank_name': bank_name_value,
                'partner_bank_account': bank_account_value,
            })
        return lines

    @api.model
    def _convert_line_to_transactions(self, line):
        transactions = []

        transaction_id = line['transaction_id']
        invoice = line['invoice']
        description = line['description']
        details = line['details']
        timestamp = line['timestamp']
        gross_amount = line['gross_amount']
        fee_amount = line['fee_amount']
        payer_name = line['payer_name']
        payer_email = line['payer_email']
        partner_bank_account = line['partner_bank_account']

        if invoice:
            invoice = _('Invoice %s') % invoice
        note = '%s %s' % (
            description,
            transaction_id,
        )
        if details:
            note += ': %s' % details
        if payer_email:
            note += ' (%s)' % payer_email

        unique_import_id = '%s-%s' % (
            transaction_id,
            int(timestamp.timestamp()),
        )
        name = invoice or details or description or '',
        transaction = {
            'name': invoice or details or description or '',
            'amount': str(gross_amount),
            'date': timestamp,
            'note': note,
            'unique_import_id': unique_import_id,
        }
        if payer_name:
            line.update({
                'partner_name': payer_name,
            })
        if partner_bank_account:
            line.update({
                'account_number': partner_bank_account,
            })
        transactions.append(transaction)

        if fee_amount:
            transactions.append({
                'name': _('Fee for %s') % (name or transaction_id),
                'amount': str(fee_amount),
                'date': timestamp,
                'partner_name': 'PayPal',
                'unique_import_id': '%s-FEE' % unique_import_id,
                'note': _('Transaction fee for %s') % note,
            })
        return transactions

    @api.model
    def _parse_decimal(self, value, mapping):
        thousands, decimal = mapping._get_float_separators()
        value = value.replace(thousands, '')
        value = value.replace(decimal, '.')
        return Decimal(value)

    @api.model
    def _normalize_tz(self, value):
        if value in ['PDT', 'PST']:
            return 'PST8PDT'
        return value
