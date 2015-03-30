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
import re

from openerp.addons.bank_statement_parse_mt940 import mt940


class MT940Parser(mt940.MT940):
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

    def handle_tag_25(self, data):
        """ING: For current accounts: IBAN+ ISO 4217 currency code."""
        self.current_statement.local_account = data[:-3]

    def handle_tag_61(self, data):
        """get transaction values"""
        super(MT940Parser, self).handle_tag_61(data)
        re_61 = self.tag_61_regex.match(data)
        if not re_61:
            raise ValueError("Cannot parse %s" % data)
        parsed_data = re_61.groupdict()
        self.current_transaction.transferred_amount = (
            mt940.str2amount(parsed_data['sign'], parsed_data['amount']))
        self.current_transaction.eref = parsed_data['reference']

    def handle_tag_86(self, data):
        """Parse 86 tag containing reference data."""
        if not self.current_transaction:
            return
        super(MT940Parser, self).handle_tag_86(data)
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

        if self.current_transaction.eref in subfields:
            self.current_transaction.eref = ''.join(
                subfields[self.current_transaction.eref])

        if not subfields:
            self.current_transaction.message = data

        self.current_transaction = None

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
