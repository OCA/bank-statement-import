# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2017 Giedrius Slavinskas <giedrius@inovera.lt>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import re
import logging
from openerp import models
from openerp.addons.account_bank_statement_import_mt940_base.mt940 import (
    MT940, str2amount)


logger = logging.getLogger(__name__)

tag_61_regex = re.compile(
    r'^(?P<date>\d{6})(?P<line_date>\d{0,4})?'
    r'(?P<sign>[CD])(?P<currency>[A-Z])?(?P<amount>\d+,\d{2})N'
    r'(?P<type>.{3})(?P<reference>.{16})//(?P<bankref>.{16})(?P<info>.*)'
)


class MT940Parser(MT940):
    """Parser for ing MT940 bank statement import files."""

    def __init__(self):
        """Initialize parser - override at least header_regex."""
        super(MT940Parser, self).__init__()
        self.mt940_type = 'UK HSBC'
        self.header_lines = 0
        self.header_regex = '^:20:\d{6}'
        self.footer_regex = '^:62F:'

    def handle_tag_20(self, data):
        """get bank statment file reference"""
        super(MT940Parser, self).handle_header(data, None)
        self.current_statement.ref = data.strip()

    def handle_tag_25(self, data):
        """parse local bank account number of the bank statment"""
        data = data.strip()
        self.current_statement.local_account = ' '.join([data[:6],
                                                         data[6:].zfill(8)])

    def handle_tag_28C(self, data):
        """get bank statment file number"""
        self.current_statement.number = data.strip()

    def handle_tag_61(self, data):
        """get transaction values"""
        super(MT940Parser, self).handle_tag_61(data)

        match = tag_61_regex.match(data)
        if not match:
            raise ValueError("Cannot parse %s" % data)
        res = match.groupdict()

        transaction = self.current_transaction
        transaction.transferred_amount = str2amount(res['sign'], res['amount'])
        transaction.transfer_type = res['type']

        res['reference'] = res['reference'].strip()
        if res['reference'] and res['reference'] != 'NONREF':
            transaction.eref = res['reference']

    def handle_tag_86(self, data):
        """set additional info"""
        self.current_transaction.message = ' '.join(data.split())

    def handle_header(self, dummy_line, iterator):
        pass

    def handle_footer(self, dummy_line, dummy_iterator):
        self.handle_record(dummy_line)
        statement = self.current_statement
        statement.statement_id = '%s-%s-%s' % (
            statement.ref, statement.local_account, statement.number
        )
        super(MT940Parser, self).handle_footer(dummy_line, dummy_iterator)


class AccountBankStatementImport(models.TransientModel):
    """Add parsing of mt940 files to bank statement import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
        """Parse a MT940 UK HSBC file."""
        parser = MT940Parser()
        try:
            logger.debug("Try parsing with MT940 UK HSBC.")
            return parser.parse(data_file)
        except ValueError:
            # Returning super will call next candidate:
            logger.debug("Statement file was not a MT940 UK HSBC file.",
                          exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)
