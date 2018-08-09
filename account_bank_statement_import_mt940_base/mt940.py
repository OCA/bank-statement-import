# -*- coding: utf-8 -*-
# Copyright (C) 2014-2015 Therp BV <http://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Generic parser for MT940 files, base for customized versions per bank."""

import re
import logging
from datetime import datetime


def str2amount(sign, amount_str):
    """Convert sign (C or D) and amount in string to signed amount (float)."""
    factor = (1 if sign == 'C' else -1)
    return factor * float(amount_str.replace(',', '.'))


def get_subfields(data, codewords):
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


def get_counterpart(transaction, subfield):
    """Get counterpart from transaction.

    Counterpart is often stored in subfield of tag 86. The subfield
    can be BENM, ORDP, CNTP"""
    if not subfield:
        return  # subfield is empty
    if len(subfield) >= 1 and subfield[0]:
        transaction.update({'account_number': subfield[0]})
    if len(subfield) >= 2 and subfield[1]:
        transaction.update({'account_bic': subfield[1]})
    if len(subfield) >= 3 and subfield[2]:
        transaction.update({'partner_name': subfield[2]})


def handle_common_subfields(transaction, subfields):
    """Deal with common functionality for tag 86 subfields."""
    # Get counterpart from CNTP, BENM or ORDP subfields:
    for counterpart_field in ['CNTP', 'BENM', 'ORDP']:
        if counterpart_field in subfields:
            get_counterpart(transaction, subfields[counterpart_field])
    if not transaction.get('name'):
        transaction['name'] = ''
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


class MT940(object):
    """Inherit this class in your account_banking.parsers.models.parser,
    define functions to handle the tags you need to handle and adjust static
    variables as needed.

    At least, you should override handle_tag_61 and handle_tag_86.
    Don't forget to call super.

    handle_tag_* functions receive the remainder of the the line (that is,
    without ':XX:') and are supposed to write into self.current_transaction
    """

    def __init__(self):
        """Initialize parser - override at least header_regex.

        This in fact uses the ING syntax, override in others."""
        self.mt940_type = 'General'
        self.header_lines = 3  # Number of lines to skip
        self.header_regex = '^0000 01INGBNL2AXXXX|^{1'  # Start of header
        self.footer_regex = '^-}$|^-XXX$'  # Stop processing on seeing this
        self.tag_regex = '^:[0-9]{2}[A-Z]*:'  # Start of new tag
        self.current_statement = None
        self.current_transaction = None
        self.statements = []
        self.currency_code = None
        self.account_number = None

    def is_mt940(self, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.header_regex, line)):
            raise ValueError(
                'File starting with %s does not seem to be a'
                ' valid %s MT940 format bank statement.' %
                (line[:12], self.mt940_type)
            )

    def is_mt940_statement(self, line):
        """determine if line is the start of a statement"""
        if not bool(line.startswith('{4:')):
            raise ValueError(
                'The pre processed match %s does not seem to be a'
                ' valid %s MT940 format bank statement. Every statement'
                ' should start be a dict starting with {4:..' % line
            )

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
        matches = self.pre_process_data(data)
        for match in matches:
            self.is_mt940_statement(line=match)
            iterator = '\n'.join(
                match.split('\n')[1:-1]).split('\n').__iter__()
            line = None
            record_line = ''
            try:
                while True:
                    if not self.current_statement:
                        self.handle_header(line, iterator,
                                           header_lines=header_lines)
                    line = iterator.next()
                    if not self.is_tag(line) and not self.is_footer(line):
                        record_line = self.add_record_line(line, record_line)
                        continue
                    if record_line:
                        self.handle_record(record_line)
                    if self.is_footer(line):
                        self.handle_footer(line, iterator)
                        record_line = ''
                        continue
                    record_line = line
            except StopIteration:
                pass
            if self.current_statement:
                if record_line:
                    self.handle_record(record_line)
                    record_line = ''
                self.statements.append(self.current_statement)
                self.current_statement = None
        return self.currency_code, self.account_number, self.statements

    def add_record_line(self, line, record_line):
        record_line += line
        return record_line

    def is_footer(self, line):
        """determine if a line is the footer of a statement"""
        return line and bool(re.match(self.footer_regex, line))

    def is_tag(self, line):
        """determine if a line has a tag"""
        return line and bool(re.match(self.tag_regex, line))

    def handle_header(self, dummy_line, iterator, header_lines=None):
        """skip header lines, create current statement"""
        if not header_lines:
            header_lines = self.header_lines
        for dummy_i in range(header_lines):
            iterator.next()
        self.current_statement = {
            'name': None,
            'date': None,
            'balance_start': 0.0,
            'balance_end_real': 0.0,
            'transactions': []
        }

    def handle_footer(self, dummy_line, dummy_iterator):
        """add current statement to list, reset state"""
        self.statements.append(self.current_statement)
        self.current_statement = None

    def handle_record(self, line):
        """find a function to handle the record represented by line"""
        tag_match = re.match(self.tag_regex, line)
        tag = tag_match.group(0).strip(':')
        if not hasattr(self, 'handle_tag_%s' % tag):  # pragma: no cover
            logging.error('Unknown tag %s', tag)
            logging.error(line)
            return
        handler = getattr(self, 'handle_tag_%s' % tag)
        handler(line[tag_match.end():])

    def handle_tag_20(self, data):
        """Contains unique ? message ID"""
        pass

    def handle_tag_25(self, data):
        """Handle tag 25: local bank account information."""
        data = data.replace('EUR', '').replace('.', '').strip()
        self.account_number = data

    def handle_tag_28C(self, data):
        """Sequence number within batch - normally only zeroes."""
        pass

    def handle_tag_60F(self, data):
        """get start balance and currency"""
        # For the moment only first 60F record
        # The alternative would be to split the file and start a new
        # statement for each 20: tag encountered.
        if not self.currency_code:
            self.currency_code = data[7:10]
        self.current_statement['balance_start'] = str2amount(
            data[0],
            data[10:]
        )
        if not self.current_statement['date']:
            self.current_statement['date'] = datetime.strptime(data[1:7],
                                                               '%y%m%d')

    def handle_tag_61(self, data):
        """get transaction values"""
        self.current_statement['transactions'].append({})
        self.current_transaction = self.current_statement['transactions'][-1]
        self.current_transaction['date'] = datetime.strptime(
            data[:6],
            '%y%m%d'
        )

    def handle_tag_62F(self, data):
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

        self.current_statement['balance_end_real'] = str2amount(
            data[0],
            data[10:]
        )
        self.current_statement['date'] = datetime.strptime(data[1:7], '%y%m%d')

        # Only replace logically empty (only whitespace or zeroes) id's:
        # But do replace statement_id's added before (therefore starting
        # with local_account), because we need the date on the last 62F
        # record.
        statement_name = self.current_statement['name'] or ''
        test_empty_id = re.sub(r'[\s0]', '', statement_name)
        is_account_number = statement_name.startswith(self.account_number)
        if not test_empty_id or is_account_number:
            self.current_statement['name'] = '%s-%s' % (
                self.account_number,
                self.current_statement['date'].strftime('%Y-%m-%d'),
            )

    def handle_tag_64(self, data):
        """get current balance in currency"""
        pass

    def handle_tag_65(self, data):
        """get future balance in currency"""
        pass

    def handle_tag_86(self, data):
        """details for previous transaction, here most differences between
        banks occur"""
        pass
