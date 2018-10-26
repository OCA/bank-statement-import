# -*- coding: utf-8 -*-
# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import StringIO
import dateutil.parser

from odoo.tools.translate import _
from odoo import api, models
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

try:
    import chardet
except (ImportError, IOError) as err:
    chardet = False
    _logger.debug(err)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    @api.model
    def _check_qif(self, data_file):
        return data_file.strip().startswith('!Type:')

    def _get_qif_encoding(self, data_file):
        if chardet:
            return chardet.detect(data_file)['encoding']
        else:
            return u'utf-8'

    def _parse_qif_date(self, date_str, qif_date_format):
        date_args = {
            'fuzzy': True
        }
        if qif_date_format == 'dmy':
            date_args.update({'dayfirst': True})
        elif qif_date_format == 'mdy':
            date_args.update({'dayfirst': False})
        elif qif_date_format == 'ymd':
            date_args.update({'yearfirst': True})
        return dateutil.parser.parse(date_str, **date_args).date()

    def _parse_file(self, data_file):
        if not self._check_qif(data_file):
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        qif_date_format = False
        journal_id = self.env.context.get('journal_id')
        if journal_id:
            journal = self.env['account.journal'].browse(journal_id)
            qif_date_format = journal.qif_date_format
        encoding = self._get_qif_encoding(data_file)
        data_file = data_file.decode(encoding)
        try:
            file_data = ""
            for line in StringIO.StringIO(data_file).readlines():
                file_data += line
            if '\r' in file_data:
                data_list = file_data.split('\r')
            else:
                data_list = file_data.split('\n')
            header = data_list[0].strip()
            header = header.split(":")[1]
        except:
            raise UserError(_('Could not decipher the QIF file.'))
        transactions = []
        vals_line = {}
        total = 0
        if header in ("Bank", "CCard"):
            vals_bank_statement = {}
            for line in data_list:
                line = line.strip()
                if not line:
                    continue
                if line[0] == 'D':  # date of transaction
                    vals_line['date'] = self._parse_qif_date(line[1:],
                                                             qif_date_format)
                elif line[0] == 'T':  # Total amount
                    total += float(line[1:].replace(',', ''))
                    vals_line['amount'] = float(line[1:].replace(',', ''))
                elif line[0] == 'N':  # Check number
                    vals_line['ref'] = line[1:]
                elif line[0] == 'P':  # Payee
                    vals_line['name'] = (
                        'name' in vals_line and
                        line[1:] + ': ' + vals_line['name'] or line[1:]
                    )
                elif line[0] == 'M':  # Memo
                    vals_line['name'] = ('name' in vals_line and
                                         vals_line['name'] + ': ' + line[1:] or
                                         line[1:])
                elif line[0] == '^':  # end of item
                    transactions.append(vals_line)
                    vals_line = {}
                elif line[0] == '\n':
                    transactions = []
                else:
                    pass
        else:
            raise UserError(_('This file is either not a bank statement or is '
                              'not correctly formed.'))
        vals_bank_statement.update({
            'balance_end_real': total,
            'transactions': transactions
        })
        return None, None, [vals_bank_statement]

    def _complete_stmts_vals(self, stmt_vals, journal_id, account_number):
        """Match partner_id if hasn't been deducted yet."""
        res = super(AccountBankStatementImport, self)._complete_stmts_vals(
            stmt_vals, journal_id, account_number,
        )
        # Since QIF doesn't provide account numbers (normal behaviour is to
        # provide 'account_number', which the generic module uses to find
        # the partner), we have to find res.partner through the name
        partner_obj = self.env['res.partner']
        for statement in res:
            for line_vals in statement['transactions']:
                if not line_vals.get('partner_id') and line_vals.get('name'):
                    partner = partner_obj.search(
                        [('name', 'ilike', line_vals['name'])], limit=1,
                    )
                    line_vals['partner_id'] = partner.id
        return res
