# -*- coding: utf-8 -*-
"""Implement parser for MT940 files - Rabobank dialect."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
import re
from string import printable
from openerp.addons.account_bank_statement_import_mt940_base.mt940 import (
    MT940, str2amount, get_subfields, handle_common_subfields)


class MT940Parser(MT940):
    """Implement parser for MT940 files - Rabobank dialect."""

    tag_61_regex = re.compile(
        r'^(?P<date>\d{6})(?P<sign>[CD])(?P<amount>\d+,\d{2})N(?P<type>.{3})'
        r'(?P<reference>MARF|EREF|PREF|NONREF)\s*'
        r'\n?(?P<remote_account>\w{1,34})?'
    )

    def __init__(self):
        """Initialize parser - override at least header_regex."""
        super(MT940Parser, self).__init__()
        self.mt940_type = 'RABO'
        self.header_lines = 1  # Number of lines to skip
        # Do not user $ for end of string below: line contains much
        # more data than just the first line.
        self.header_regex = '^:940:'  # Start of relevant data

    def parse(self, data):
        """Filter Unprintable characters from file data.

        The file contents of the Rabobank tend to contain unprintable
        characters that prevent proper parsing. These will be removed.
        """
        data = ''.join([x for x in data if x in printable])
        return super(MT940Parser, self).parse(data)

    def handle_tag_61(self, data):
        """Handle tag 61: transaction data."""
        super(MT940Parser, self).handle_tag_61(data)
        parsed_data = self.tag_61_regex.match(data).groupdict()
        self.current_transaction.transferred_amount = (
            str2amount(parsed_data['sign'], parsed_data['amount']))
        self.current_transaction.eref = parsed_data['reference']
        if parsed_data['remote_account']:
            self.current_transaction.remote_account = (
                parsed_data['remote_account'])

    def handle_tag_86(self, data):
        """Handle tag 86: transaction details"""
        if not self.current_transaction:
            return
        codewords = ['RTRN', 'BENM', 'ORDP', 'CSID', 'BUSP', 'MARF', 'EREF',
                     'PREF', 'REMI', 'ID', 'PURP', 'ULTB', 'ULTD',
                     'CREF', 'IREF', 'NAME', 'ADDR', 'ULTC', 'EXCH', 'CHGS']
        subfields = get_subfields(data, codewords)
        transaction = self.current_transaction
        # If we have no subfields, set message to whole of data passed:
        if not subfields:
            transaction.message = data
        else:
            handle_common_subfields(transaction, subfields)
            # Use subfields for transaction details:
            if 'NAME' in subfields:
                transaction.remote_owner = ' '.join(subfields['NAME'])
            if 'ADDR' in subfields:
                # Do NOT join address fields, array is expected on other code!
                transaction.remote_owner_address = subfields['ADDR']
        # Prevent handling tag 86 later for non transaction details:
        self.current_transaction = None
