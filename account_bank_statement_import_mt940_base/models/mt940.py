# Copyright (C) 2014-2015 Therp BV <http://therp.nl>.
# Copyright 2019 OdooERP Romania <https://odooerpromania.ro>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Generic parser for MT940 files, base for customized versions per bank."""

import re
import logging
from string import printable
from datetime import datetime

from odoo import models


class MT940Parser(models.AbstractModel):
    _name = 'account.bank.statement.import.mt940.parser'
    _description = 'Account Bank Statement Import MT940 Parser'
    """ Inherit this class in your account_banking.parsers.models.parser,
        define functions to handle the tags you need to handle and adjust
        methods depending on get_mt940_type to return right result.
        The type is defined in context in _parse_file of
        account_bank_statement_import.

        At least, you should override handle_tag_61 and handle_tag_86.
        Don't forget to call super.

        handle_tag_* functions receive the remainder of the the line (that is,
        without ':XX:') and are supposed to write into current transaction.
    """

    def get_mt940_type(self):
        return self.env.context.get('type')

    def get_header_lines(self):
        # Works implicit for general and rabo
        return 0

    def get_header_regex(self):
        # Works implicit for general (rabo)
        return ':940:'

    def get_footer_regex(self):
        # Works implicit for general (rabo)
        return '}'

    def get_tag_regex(self):
        return '^:[0-9]{2}[A-Z]*:'

    def get_codewords(self):
        return ['BENM', 'ADDR', 'NAME', 'CNTP', 'ISDT', 'REMI']

    def get_tag_61_regex(self):
        return re.compile(
            r'^(?P<date>\d{6})(?P<line_date>\d{0,4})'
            r'(?P<sign>[CD])(?P<amount>\d+,\d{2})N(?P<type>.{3})'
            r'(?P<reference>\w{1,50})'
        )

    def is_mt940(self, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.get_header_regex(), line)):
            raise ValueError(
                'File starting with %s does not seem to be a'
                ' valid %s MT940 format bank statement.' %
                (line[:12], self.get_mt940_type())
            )

    def is_mt940_statement(self, line):
        """determine if line is the start of a statement"""
        if not bool(line.startswith('{4:')):
            raise ValueError(
                'The pre processed match %s does not seem to be a'
                ' valid %s MT940 format bank statement. Every statement'
                ' should start be a dict starting with {4:..' % line
            )

    def parse_amount(self, sign, amount_str):
        """Convert sign (C or D) and amount in string to signed
        amount (float)."""
        factor = (1 if sign == 'C' else -1)
        return factor * float(amount_str.replace(',', '.'))

    def get_subfields(self, data, codewords):
        """Return dictionary with value array for each codeword in data.

        For instance:
        data =
            /BENM//NAME/Kosten/REMI/Periode 01-10-2013 t/m 31-12-2013/ISDT/20
        codewords = ['BENM', 'ADDR', 'NAME', 'CNTP', ISDT', 'REMI']
        Then return subfields = {
            'BENM': [],
            'NAME': ['Kosten'],
            'REMI': ['Periode 01-10-2013 t', 'm 31-12-2013'],
            'ISDT': ['20'],
        }
        """
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
        return subfields

    def get_counterpart(self, transaction, subfield):
        """Get counterpart from transaction.

        Counterpart is often stored in subfield of tag 86. The subfield
        can be BENM, ORDP, CNTP"""
        if not subfield:
            return  # subfield is empty
        subfield = list(filter(lambda a: a != '', subfield))
        if len(subfield) >= 1 and subfield[0]:
            transaction.update({'account_number': subfield[0]})
        if len(subfield) >= 3 and subfield[2]:
            transaction.update({'partner_name': subfield[2]})
        return transaction

    def handle_common_subfields(self, transaction, subfields):
        """Deal with common functionality for tag 86 subfields."""
        # Get counterpart from CNTP, BENM or ORDP subfields:
        for counterpart_field in ['CNTP', 'BENM', 'ORDP']:
            if counterpart_field in subfields:
                self.get_counterpart(transaction,
                                     subfields[counterpart_field])
        if not transaction.get('name'):
            transaction['name'] = '/'
        # REMI: Remitter information (text entered by other party on trans.):
        if 'REMI' in subfields:
            transaction['name'] += (
                subfields['REMI'][2]
                # this might look like
                # /REMI/USTD//<remittance info>/
                # or
                # /REMI/STRD/CUR/<betalingskenmerk>/
                if len(subfields['REMI']) >= 3 and subfields['REMI'][0] in [
                    'STRD', 'USTD'
                ]
                else
                '/'.join(x for x in subfields['REMI'] if x)
            )
        # EREF: End-to-end reference
        if 'EREF' in subfields:
            transaction['name'] += '/'.join(filter(bool, subfields['EREF']))
        # Get transaction reference subfield (might vary):
        if transaction.get('ref') in subfields:
            transaction['ref'] = ''.join(subfields[transaction['ref']])

    def pre_process_data(self, data):
        matches = []
        self.is_mt940(line=data)
        data = data.replace(
            '-}', '}').replace('}{', '}\r\n{').replace('\r\n', '\n')
        if data.startswith(':940:'):
            for statement in data.replace(':940:', '').split(':20:'):
                match = '{4:\n:20:' + statement + '}'
                matches.append(match)
        else:
            tag_re = re.compile(
                r'(\{4:[^{}]+\})',
                re.MULTILINE)
            matches = tag_re.findall(data)
        return matches

    def parse(self, data, header_lines=None):
        """Parse mt940 bank statement file contents."""
        data = data.decode()
        data = ''.join([str(x) for x in data if str(x) in printable])

        matches = self.pre_process_data(data)
        statements = []
        result = {
            'currency': None,
            'account_number': None,
            'statement': None,
        }
        if not header_lines:
            header_lines = self.get_header_lines()
        for match in matches:
            self.is_mt940_statement(line=match)
            iterator = '\n'.join(
                match.split('\n')[1:-1]).split('\n').__iter__()
            line = None
            record_line = ''
            try:
                while True:
                    if not result['statement']:
                        result['statement'] = self.handle_header(iterator,
                                                                 header_lines)
                    line = next(iterator)
                    if not self.is_tag(line) and not self.is_footer(line):
                        record_line = self.add_record_line(line, record_line)
                        continue
                    if record_line:
                        self.handle_record(record_line, result)
                    if self.is_footer(line):
                        statements.append(result['statement'])
                        result['statement'] = None
                        record_line = ''
                        continue
                    record_line = line
            except StopIteration:
                pass
            if result['statement']:
                if record_line:
                    self.handle_record(record_line, result)
                statements.append(result['statement'])
                result['statement'] = None
        return result['currency'], result['account_number'], statements

    def add_record_line(self, line, record_line):
        record_line += line
        return record_line

    def is_footer(self, line):
        """determine if a line is the footer of a statement"""
        return line and bool(re.match(self.get_footer_regex(), line))

    def is_tag(self, line):
        """determine if a line has a tag"""
        return line and bool(re.match(self.get_tag_regex(), line))

    def handle_header(self, iterator, header_lines=None):
        """skip header lines, create current statement"""
        if not header_lines:
            header_lines = self.get_header_lines()
        for dummy_i in range(header_lines):
            next(iterator)
        current_statement = {
            'name': None,
            'date': None,
            'balance_start': 0.0,
            'balance_end_real': 0.0,
            'transactions': []
        }
        return current_statement

    def handle_record(self, line, result):
        """find a function to handle the record represented by line"""
        tag_match = re.match(self.get_tag_regex(), line)
        if tag_match:
            tag = tag_match.group(0).strip(':')
            if not hasattr(self, 'handle_tag_%s' % tag):  # pragma: no cover
                logging.error('Unknown tag %s', tag)
                logging.error(line)
                return
            handler = getattr(self, 'handle_tag_%s' % tag)
            result = handler(line[tag_match.end():], result)
        return result

    def handle_tag_20(self, data, result):
        """Contains unique ? message ID"""
        return result

    def handle_tag_25(self, data, result):
        """Handle tag 25: local bank account information."""
        data = data.replace('EUR', '').replace('.', '').strip()
        result['account_number'] = data
        return result

    def handle_tag_28C(self, data, result):
        """Sequence number within batch - normally only zeroes."""
        return result

    def handle_tag_60F(self, data, result):
        """get start balance and currency"""
        # For the moment only first 60F record
        # The alternative would be to split the file and start a new
        # statement for each 20: tag encountered.
        if not result['currency']:
            result['currency'] = data[7:10]
        if result['statement']:
            result['statement']['balance_start'] = self.parse_amount(
                data[0], data[10:]
            )
            if not result['statement']['date']:
                result['statement']['date'] = datetime.strptime(
                    data[1:7], '%y%m%d'
                )
        return result

    def handle_tag_61(self, data, result):
        """get transaction values"""
        tag_61_regex = self.get_tag_61_regex()
        re_61 = tag_61_regex.match(data)
        if not re_61:
            raise ValueError("Cannot parse %s" % data)
        parsed_data = re_61.groupdict()
        if parsed_data and result['statement']:
            result['statement']['transactions'].append({})
            transaction = result['statement']['transactions'][-1]
            transaction['date'] = datetime.strptime(
                data[:6],
                '%y%m%d'
            )
            transaction['amount'] = self.parse_amount(
                parsed_data['sign'], parsed_data['amount'])
            transaction['note'] = parsed_data['reference']
        return result

    def handle_tag_62F(self, data, result):
        """Get ending balance, statement date and id.

        We use the date on the last 62F tag as statement date, as the date
        on the 60F record (previous end balance) might contain a date in
        a previous period.

        We generate the statement.id from the local_account and the end-date,
        this should normally be unique, provided there is a maximum of
        one statement per day.

        Depending on the bank, there might be multiple 62F tags in the import
        file. The last one counts.
        """
        if result['statement']:
            result['statement']['balance_end_real'] = self.parse_amount(
                data[0],
                data[10:]
            )
            result['statement']['date'] = datetime.strptime(data[1:7], '%y%m%d')

            # Only replace logically empty (only whitespace or zeroes) id's:
            # But do replace statement_id's added before (therefore starting
            # with local_account), because we need the date on the last 62F
            # record.
            statement_name = result['statement']['name'] or ''
            test_empty_name = re.sub(r'[\s0]', '', statement_name)
            if result['statement']['name'] is None or test_empty_name:
                if result['account_number']:
                    result['statement']['name'] = result['account_number']
            if statement_name:
                is_account_number = statement_name.startswith(
                    result['account_number'])
                if is_account_number and result['statement']['date']:
                    result['statement']['name'] += ' - ' + \
                        result['statement']['date'].strftime('%Y-%m-%d')
        return result

    def handle_tag_64(self, data, result):
        """get current balance in currency"""
        return result

    def handle_tag_65(self, data, result):
        """get future balance in currency"""
        return result

    def handle_tag_86(self, data, result):
        """details for previous transaction, here most differences between
        banks occur"""
        if result['statement']['transactions']:
            transaction = result['statement']['transactions'][-1]
            codewords = self.get_codewords()
            subfields = self.get_subfields(data, codewords)
            self.handle_common_subfields(transaction, subfields)
        return result
