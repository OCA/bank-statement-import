# -*- encoding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_paypal module for Odoo
#    Copyright (C) 2014-2015 Akretion (http://www.akretion.com)
#    @author Alexis de Lattre <alexis.delattre@akretion.com>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import logging
from datetime import datetime
from openerp import models, fields, api, _
from openerp.exceptions import Warning
import unicodecsv
import re
from cStringIO import StringIO

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _prepare_paypal_encoding(self):
        '''This method is designed to be inherited'''
        return 'latin1'

    @api.model
    def _prepare_paypal_date_format(self):
        '''This method is designed to be inherited'''
        return '%d/%m/%Y'

    @api.model
    def _valid_paypal_line(self, line):
        '''This method is designed to be inherited'''
        if line[5].startswith('Termin'):
            return True
        else:
            return False

    @api.model
    def _paypal_convert_amount(self, amount_str):
        '''This method is designed to be inherited'''
        valstr = re.sub(r'[^\d,.-]', '', amount_str)
        valstrdot = valstr.replace(',', '.')
        return float(valstrdot)

    @api.model
    def _check_paypal(self, data_file):
        '''This method is designed to be inherited'''
        return data_file.strip().startswith('Date,')

    @api.model
    def _parse_file(self, data_file):
        """ Import a file in Paypal CSV format"""
        paypal = self._check_paypal(data_file)
        if not paypal:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        f = StringIO()
        f.write(data_file)
        f.seek(0)
        transactions = []
        i = 0
        start_balance = end_balance = start_date_str = end_date_str = False
        vals_line = False
        company_currency_name = self.env.user.company_id.currency_id.name
        commission_total = 0.0
        raw_lines = []
        paypal_email_account = False
        # To confirm : is the encoding always latin1 ?
        for line in unicodecsv.reader(
                f, encoding=self._prepare_paypal_encoding()):
            i += 1
            _logger.debug("Line %d: %s" % (i, line))
            if i == 1:
                _logger.debug('Skip header line')
                continue
            if not line:
                continue
            if not self._valid_paypal_line(line):
                _logger.info(
                    'Skipping line %d because it is not in Done state' % i)
                continue
            date_dt = datetime.strptime(
                line[0], self._prepare_paypal_date_format())
            rline = {
                'date': fields.Date.to_string(date_dt),
                'currency': line[6],
                'owner_name': line[3],
                'amount': line[7],
                'commission': line[8],
                'balance': line[34],
                'transac_ref': line[30],
                'ref': line[12],
                'line_nr': i,
            }
            for field in ['commission', 'amount', 'balance']:
                _logger.debug('Trying to convert %s to float' % rline[field])
                try:
                    rline[field] = self._paypal_convert_amount(rline[field])
                except:
                    raise Warning(
                        _("Value '%s' for the field '%s' on line %d, "
                            "cannot be converted to float")
                        % (rline[field], field, i))
            if rline['amount'] > 0:
                rline['name'] = line[3] + ' ' + line[10]
                rline['partner_email'] = line[10]
                if not paypal_email_account:
                    paypal_email_account = line[11]
            else:
                rline['name'] = line[3] + ' ' + line[11]
                rline['partner_email'] = line[11]
                if not paypal_email_account:
                    paypal_email_account = line[10]
            raw_lines.append(rline)

        # Second pass to sort out the lines in other currencies
        final_lines = []
        other_currency_line = {}
        for wline in raw_lines:
            if company_currency_name != wline['currency']:
                if not wline['transac_ref'] and not other_currency_line:
                    currencies = self.env['res.currency'].search(
                        [('name', '=', wline['currency'])])
                    if not currencies:
                        raise Warning(
                            _('Currency %s on line %d cannot be found in Odoo')
                            % (wline['currency'], wline['line_nr']))
                    other_currency_line = {
                        'amount_currency': wline['amount'],
                        'currency_id': currencies[0].id,
                        'currency': wline['currency'],
                        'name': wline['name'],
                        'owner_name': wline['owner_name'],
                        }
                if wline['transac_ref'] and other_currency_line:
                    assert (
                        wline['currency'] == other_currency_line['currency']),\
                        'WRONG currency'
                    assert (
                        wline['amount'] ==
                        other_currency_line['amount_currency'] * -1),\
                        'WRONG amount'
                    other_currency_line['transac_ref'] = wline['transac_ref']
            else:
                if (
                        other_currency_line
                        and wline['transac_ref'] ==
                        other_currency_line['transac_ref']):
                    wline.update(other_currency_line)
                    # reset other_currency_line
                    other_currency_line = {}
                final_lines.append(wline)

        # PayPal statements start with the end !
        final_lines.reverse()
        j = 0
        for fline in final_lines:
            j += 1
            commission_total += fline['commission']

            if j == 1:
                start_date_str = fline['date']
                start_balance = fline['balance'] - fline['amount']
            end_date_str = fline['date']
            end_balance = fline['balance']
            partners = False
            if fline['partner_email']:
                partners = self.env['res.partner'].search(
                    [('email', '=', fline['partner_email'])])
            if partners:
                partner_id = partners[0].commercial_partner_id.id
            else:
                partner_id = False
            vals_line = {
                'date': fline['date'],
                'name': fline['name'],
                'ref': fline['ref'],
                'unique_import_id': fline['ref'],
                'amount': fline['amount'],
                'partner_id': partner_id,
                'bank_account_id': False,
                'currency_id': fline.get('currency_id'),
                'amount_currency': fline.get('amount_currency'),
                }
            _logger.debug("vals_line = %s" % vals_line)
            transactions.append(vals_line)

        if commission_total:
            commission_line = {
                'date': end_date_str,
                'name': _('Paypal commissions'),
                'ref': _('PAYPAL-COSTS'),
                'amount': commission_total,
                'unique_import_id': False,
                }
            transactions.append(commission_line)

        vals_bank_statement = {
            'name': _('PayPal Import %s > %s')
            % (start_date_str, end_date_str),
            'balance_start': start_balance,
            'balance_end_real': end_balance,
            'transactions': transactions,
        }
        return None, paypal_email_account, [vals_bank_statement]
