##############################################################################
#
#    Copyright (C) 2017 Xpansa Group (<http://xpansa.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import re
from openerp.addons.account_bank_statement_import_mt940_base.mt940 import MT940

import logging
_logger = logging.getLogger(__name__)


class MT940Parser(MT940):
    """ parser for MT940 bank statement import files
    """

    tag_61_regex = re.compile(
        r'^(?P<date>\d{6})'
        r'(?P<line_date>\d{0,4})'
        r'(?P<sign>[R]{0,1}[CD])'
        r'(?P<currency>[NDR])'
        r'(?P<amount>\d+,\d{2})'
        r'(N|S)(?P<type>.{3})'
        r'(?P<reference>\w{0,16})'
        r'//'
        r'(?P<rzbid>\w{16}){0,1}'
    )

    def __init__(self):
        """ Raiffeisen MT940 parser initialization
        """
        super(MT940Parser, self).__init__()

        self.mt940_type = 'Raiffeisen'
        self.header_lines = 0
        self.header_regex = r'^:20'
        self.footer_regex = r'^\-$'
        self.tag_regex = r'^:[0-9]{2}[A-Z]*:'

    def str2amount(self, sign, amount_str):
        return (1 if sign == 'C' else -1) * float(amount_str.replace(',', '.'))

    def is_mt940_statement(self, line):
        """Determine if line is the start of a statement"""
        pass

    def pre_process_data(self, data):
        matches = []
        self.is_mt940(line=data)
        data = data.replace('\r\n', '\n')
        for statement in data.split(':20:'):
            match = '\n:20:' + statement
            matches.append(match)
        return matches

    def handle_tag_61(self, data):
        """ Process tag :61:
        """
        res = super(MT940Parser, self).handle_tag_61(data)

        re_61 = self.tag_61_regex.match(data)
        if not re_61:
            raise ValueError("Cannot parse %s" % data)
        parsed_data = re_61.groupdict()
        self.current_transaction['amount'] = (
            self.str2amount(parsed_data['sign'], parsed_data['amount'])
        )
        self.current_transaction['ref'] = parsed_data['reference']
        self.current_transaction['note'] = parsed_data['rzbid']

        return res

    def handle_tag_86(self, data):
        """ Process tag :86:
        """
        if not self.current_transaction:
            return

        subfields = self.get_subfields(data, [])
        transaction = self.current_transaction
        if not subfields:
            transaction['name'] = data
        else:
            self.handle_common_subfields(transaction, subfields)
        self.current_transaction = None

    def get_subfields(self, data, codewords):
        subfields = {}

        transaction = data.split('>', 1)
        subfields['CD'] = transaction[0]
        if not transaction[1]:
            return subfields

        for field in transaction[1].split('>'):
            if not field:
                continue
            key = field[0:2]
            value = field[2:]

            if key in ['00']:
                subfields.setdefault('type', []).append(value)
                continue
            if key in ['20', '21', '22', '23', '24', '25', '26', '27']:
                subfields.setdefault('transaction', []).append(value)
                continue
            if key in ['30']:
                subfields.setdefault('swift_code', []).append(value)
                continue
            if key in ['31']:
                subfields.setdefault('account_num', []).append(value)
                continue
            if key in ['32', '33']:
                subfields.setdefault('counterpart', []).append(value)
                continue

        return subfields

    def handle_common_subfields(self, transaction, subfields):
        if 'name' not in transaction:
            transaction['name'] = ''

        if 'swift_code' in subfields:
            transaction['account_bic'] = subfields['swift_code'][0]
        if 'account_num' in subfields:
            transaction['account_number'] = subfields['account_num'][0]
        if 'counterpart' in subfields:
            transaction['partner_name'] = ''.join(subfields['counterpart'])

        if 'type' in subfields:
            transaction['name'] += ''.join(subfields['type'])
        if 'transaction' in subfields:
            transaction['name'] += ' '
            transaction['name'] += ''.join(subfields['transaction'])
