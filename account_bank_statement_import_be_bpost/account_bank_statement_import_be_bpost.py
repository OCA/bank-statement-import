# -*- encoding: utf-8 -*-
##############################################################################
#
#    account_bank_statement_import_be_bpost module for Odoo
#    Copyright (C) 2015 Akretion (http://www.akretion.com)
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
from StringIO import StringIO
from openerp import models, fields, _
import unicodecsv

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_bpost(self, cr, uid, data_file, context=None):
        return data_file[3:].startswith(
            u'"Numéro de compte :";"'.encode('utf-8'))
        # The file starts with <U+FEFF> = UTF-8 BOM
        # http://en.wikipedia.org/wiki/Byte_order_mark

    def _parse_file(self, cr, uid, data_file, context=None):
        """ Import a file in Bpost CSV"""
        bpost = self._check_bpost(
            cr, uid, data_file, context=context)
        if not bpost:
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)
        transactions = []
        i = 0
        account_number = currency_code = False
        start_date_str = end_date_str = False
        diff = 0.0
        for line in unicodecsv.reader(
                StringIO(data_file), encoding='utf-8', delimiter=';'):
            i += 1
            _logger.debug("Line %d: %s" % (i, line))
            if i == 1:
                account_number = line[1].replace('-', '')
            if i < 3:
                continue  # skip 2 first lines
            if not line:
                continue
            name = line[7]
            if line[8]:
                name += ' - ' + line[8]
            if line[9]:
                name += ' ' + line[9]
            date = datetime.strptime(line[1], '%d-%m-%Y')
            date_str = fields.Date.to_string(date)
            amount = float(line[3].replace(',', '.'))
            diff += amount
            currency_code = line[4]
            if not start_date_str and not end_date_str:
                start_date_str = end_date_str = date_str
            elif start_date_str > date_str:
                start_date_str = date_str
            elif end_date_str < date_str:
                end_date_str = date_str
            vals_line = {
                'date': date_str,
                'name': name,
                'ref': line[10],
                'unique_import_id': '%s-%s-%s' % (date_str, amount, line[10]),
                'amount': amount,
                'partner_name': line[7],
                'account_number': line[6],
                }
            transactions.append(vals_line)

        vals_bank_statement = {
            'name': _('Bpost %s %s > %s') % (
                account_number, start_date_str, end_date_str),
            'balance_start': 0,
            'balance_end_real': 0 + diff,
            'transactions': transactions,
            }
        return currency_code, account_number, [vals_bank_statement]
