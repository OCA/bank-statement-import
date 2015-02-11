# -*- coding: utf-8 -*-
"""Implement BankStatementParser for MT940 IBAN ING files."""
##############################################################################
#
#    Copyright (C) 2013 Therp BV (<http://therp.nl>)
#    All Rights Reserved
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
from __future__ import print_function
import re
from openerp.addons.bank_statement_parse import parserlib
from openerp.addons.bank_statement_parse_mt940.mt940 import MT940, str2float


class MT940BankTransaction(parserlib.BankTransaction):
    """Override BankTransaction for different validation."""

    def __init__(self, values=None, *args, **kwargs):
        """Initialize object from values dictionary."""
        super(MT940BankTransaction, self).__init__(*args, **kwargs)
        if values:
            for attr in values:
                setattr(self, attr, values[attr])


class MT940Parser(MT940):
    """Parser for ing MT940 bank statement import files."""

    name = 'ING MT940 (structured)'
    country_code = 'NL'
    code = 'INT_MT940_STRUC'
    footer_regex = '^-}$|^-XXX$'

    tag_61_regex = re.compile(
        r'^(?P<date>\d{6})(?P<line_date>\d{0,4})'
        r'(?P<sign>[CD])(?P<amount>\d+,\d{2})N(?P<type>.{3})'
        r'(?P<reference>\w{1,50})'
    )

    def create_transaction(self, cr):
        transaction = MT940BankTransaction()
        return transaction

    def handle_tag_25(self, cr, data):
        '''ING: For current accounts: IBAN+ ISO 4217 currency code'''
        self.current_statement.local_account = data[:-3]

    def handle_tag_60F(self, cr, data):
        super(MT940Parser, self).handle_tag_60F(cr, data)
        self.current_statement.id = '%s-%s' % (
            self.current_statement.date.strftime('%Y'),
            self.current_statement.id)

    def handle_tag_61(self, cr, data):
        super(MT940Parser, self).handle_tag_61(cr, data)
        re_61 = self.tag_61_regex.match(data)
        if not re_61:
            raise ValueError("Cannot parse %s" % data)
        parsed_data = re_61.groupdict()
        self.current_transaction.transferred_amount = \
            (-1 if parsed_data['sign'] == 'D' else 1) * str2float(
                parsed_data['amount'])
        self.current_transaction.reference = parsed_data['reference']

    def handle_tag_86(self, cr, data):
        """Parse 86 tag containing reference data."""
        if not self.current_transaction:
            return
        super(MT940Parser, self).handle_tag_86(cr, data)
        codewords = ['RTRN', 'BENM', 'ORDP', 'CSID', 'BUSP', 'MARF', 'EREF',
                     'PREF', 'REMI', 'ID', 'PURP', 'ULTB', 'ULTD',
                     'CREF', 'IREF', 'CNTP', 'ULTC', 'EXCH', 'CHGS']
        subfields = {}
        current_codeword = None
        for word in data.split('/'):
            if not word and not current_codeword:
                continue
            if word in codewords:
                current_codeword = word
                subfields[current_codeword] = []
                continue
            if current_codeword in subfields:
                subfields[current_codeword].append(word)

        print(subfields)
        if 'CNTP' in subfields:
            self.current_transaction.remote_account = subfields['CNTP'][0]
            self.current_transaction.remote_bank_bic = subfields['CNTP'][1]
            self.current_transaction.remote_owner = subfields['CNTP'][2]
            self.current_transaction.remote_owner_city = subfields['CNTP'][3]
            self.current_transaction.remote_owner_address = None
            self.current_transaction.remote_owner_postalcode = None
            self.current_transaction.remote_owner_country_code = None

        if 'BENM' in subfields:
            self.current_transaction.remote_account = subfields['BENM'][0]
            self.current_transaction.remote_bank_bic = subfields['BENM'][1]
            self.current_transaction.remote_owner = subfields['BENM'][2]
            self.current_transaction.remote_owner_city = subfields['BENM'][3]
            self.current_transaction.remote_owner_address = None
            self.current_transaction.remote_owner_postalcode = None
            self.current_transaction.remote_owner_country_code = None

        if 'ORDP' in subfields:
            self.current_transaction.remote_account = subfields['ORDP'][0]
            self.current_transaction.remote_bank_bic = subfields['ORDP'][1]
            self.current_transaction.remote_owner = subfields['ORDP'][2]
            self.current_transaction.remote_owner_city = subfields['ORDP'][3]
            self.current_transaction.remote_owner_address = None
            self.current_transaction.remote_owner_postalcode = None
            self.current_transaction.remote_owner_country_code = None

        if 'REMI' in subfields:
            self.current_transaction.message = (
                '/'.join(x for x in subfields['REMI'] if x))

        if self.current_transaction.reference in subfields:
            self.current_transaction.reference = ''.join(
                subfields[self.current_transaction.reference])

        if not subfields:
            self.current_transaction.message = data

        self.current_transaction = None
