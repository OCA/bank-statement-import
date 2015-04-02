#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""Generic parser for MT940 files, base for customized versions per bank."""
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2014 Therp BV (<http://therp.nl>).
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
import logging
from datetime import datetime

from openerp.addons.bank_statement_parse import parserlib


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
        transaction.remote_account = subfield[0]
    if len(subfield) >= 2 and subfield[1]:
        transaction.remote_bank_bic = subfield[1]
    if len(subfield) >= 3 and subfield[2]:
        transaction.remote_owner = subfield[2]
    if len(subfield) >= 4 and subfield[3]:
        transaction.remote_owner_city = subfield[3]


def handle_common_subfields(transaction, subfields):
    """Deal with common functionality for tag 86 subfields."""
    # Get counterpart from CNTP, BENM or ORDP subfields:
    for counterpart_field in ['CNTP', 'BENM', 'ORDP']:
        if counterpart_field in subfields:
            get_counterpart(transaction, subfields[counterpart_field])
    # REMI: Remitter information (text entered by other party on trans.):
    if 'REMI' in subfields:
        transaction.message = (
            '/'.join(x for x in subfields['REMI'] if x))
    # Get transaction reference subfield (might vary):
    if transaction.eref in subfields:
        transaction.eref = ''.join(
            subfields[transaction.eref])


class MT940(object):
    """Inherit this class in your account_banking.parsers.models.parser,
    define functions to handle the tags you need to handle and adjust static
    variables as needed.

    At least, you should override handle_tag_61 and handle_tag_86.
    """

    def __init__(self):
        """Initialize parser - override at least header_regex.

        This in fact uses the ING syntax, override in others."""
        self.header_lines = 3  # Number of lines to skip
        self.header_regex = '^{1:[0-9A-Z]{25,25}}'  # Start of relevant data
        self.footer_regex = '^-}$|^-XXX$'  # Stop processing on seeing this
        self.tag_regex = '^:[0-9]{2}[A-Z]*:'  # Start of new tag
        self.current_statement = None
        self.current_transaction = None
        self.statements = []

    def create_transaction(self):
        """Create and return BankTransaction object."""
        transaction = parserlib.BankTransaction()
        return transaction

    def is_mt940(self, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.header_regex, line)):
            raise ValueError(
                'This does not seem to be a MT940 format bank statement.')

    def parse(self, data):
        """Parse mt940 bank statement file contents."""
        self.is_mt940(data)
        iterator = data.replace('\r\n', '\n').split('\n').__iter__()
        line = None
        record_line = ''
        try:
            while True:
                if not self.current_statement:
                    self.handle_header(line, iterator)
                line = iterator.next()
                if not self.is_tag(line) and not self.is_footer(line):
                    record_line = self.append_continuation_line(
                        record_line, line)
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
        return self.statements

    def append_continuation_line(self, line, continuation_line):
        """append a continuation line for a multiline record.
        Override and do data cleanups as necessary."""
        return line + continuation_line

    def create_statement(self):
        """create a BankStatement."""
        return parserlib.BankStatement()

    def is_footer(self, line):
        """determine if a line is the footer of a statement"""
        return line and bool(re.match(self.footer_regex, line))

    def is_tag(self, line):
        """determine if a line has a tag"""
        return line and bool(re.match(self.tag_regex, line))

    def handle_header(self, line, iterator):
        """skip header lines, create current statement"""
        for dummy_i in range(self.header_lines):
            iterator.next()
        self.current_statement = self.create_statement()

    def handle_footer(self, line, iterator):
        """add current statement to list, reset state"""
        self.statements.append(self.current_statement)
        self.current_statement = None

    def handle_record(self, line):
        """find a function to handle the record represented by line"""
        tag_match = re.match(self.tag_regex, line)
        tag = tag_match.group(0).strip(':')
        if not hasattr(self, 'handle_tag_%s' % tag):
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
        self.current_statement.local_account = data

    def handle_tag_28C(self, data):
        """get sequence number _within_this_batch_ - this alone
        doesn't provide a unique id!"""
        self.current_statement.statement_id = data

    def handle_tag_60F(self, data):
        """get start balance and currency"""
        self.current_statement.local_currency = data[7:10]
        self.current_statement.date = datetime.strptime(data[1:7], '%y%m%d')
        self.current_statement.start_balance = str2amount(data[0], data[10:])
        self.current_statement.statement_id = '%s/%s' % (
            self.current_statement.date.strftime('%Y-%m-%d'),
            self.current_statement.statement_id,
        )

    def handle_tag_62F(self, data):
        """get ending balance"""
        self.current_statement.end_balance = str2amount(data[0], data[10:])

    def handle_tag_64(self, data):
        """get current balance in currency"""
        pass

    def handle_tag_65(self, data):
        """get future balance in currency"""
        pass

    def handle_tag_61(self, data):
        """get transaction values"""
        transaction = self.create_transaction()
        self.current_statement.transactions.append(transaction)
        self.current_transaction = transaction
        transaction.execution_date = datetime.strptime(data[:6], '%y%m%d')
        transaction.value_date = datetime.strptime(data[:6], '%y%m%d')
        #  ...and the rest already is highly bank dependent

    def handle_tag_86(self, data):
        """details for previous transaction, here most differences between
        banks occur"""
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
