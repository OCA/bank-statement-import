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

from openerp.addons.bank_statement_parse import parserlib
from openerp.addons.bank_statement_parse.parserlib.convert import str2date
from openerp.addons.bank_statement_parse.parserlib.convert import str2float


class MT940(object):
    """Inherit this class in your account_banking.parsers.models.parser,
    define functions to handle the tags you need to handle and adjust static
    variables as needed.

    Note that order matters: You need to do your_parser(MT940, parser), not the
    other way around!

    At least, you should override handle_tag_61 and handle_tag_86. Don't forget
    to call super.
    handle_tag_* functions receive the remainder of the the line (that is,
    without ':XX:') and are supposed to write into self.current_transaction"""

    header_lines = 3
    """One file can contain multiple statements, each with its own poorly
    documented header. For now, the best thing to do seems to skip that"""

    header_regex = '^{1:[0-9A-Z]{25,25}}'
    'The file is considered a valid MT940 file when it contains this line'

    footer_regex = '^-XXX$'
    'The line that denotes end of message, we need to create a new statement'

    tag_regex = '^:[0-9]{2}[A-Z]*:'
    'The beginning of a record, should be anchored to beginning of the line'

    def __init__(self, *args, **kwargs):
        super(MT940, self).__init__(*args, **kwargs)
        self.current_statement = None
        'type account_banking.parsers.models.mem_bank_statement'
        self.current_transaction = None
        'type account_banking.parsers.models.mem_bank_transaction'
        self.statements = []
        'parsed statements up to now'

    def create_transaction(self, cr):
        """Create and return BankTransaction object."""
        transaction = parserlib.BankTransaction()
        return transaction

    def is_mt940(self, cr, line):
        """determine if a line is the header of a statement"""
        if not bool(re.match(self.header_regex, line)):
            raise ValueError(
                'This does not seem to be a MT940 IBAN ING format bank '
                'statement.')

    def parse(self, cr, data):
        """Parse mt940 bank statement file contents."""
        self.is_mt940(cr, data)
        iterator = data.replace('\r\n', '\n').split('\n').__iter__()
        line = None
        record_line = ''
        try:
            while True:
                if not self.current_statement:
                    self.handle_header(cr, line, iterator)
                line = iterator.next()
                if not self.is_tag(cr, line) and not self.is_footer(cr, line):
                    record_line = self.append_continuation_line(
                        cr, record_line, line)
                    continue
                if record_line:
                    self.handle_record(cr, record_line)
                if self.is_footer(cr, line):
                    self.handle_footer(cr, line, iterator)
                    record_line = ''
                    continue
                record_line = line
        except StopIteration:
            pass
        if self.current_statement:
            if record_line:
                self.handle_record(cr, record_line)
                record_line = ''
            self.statements.append(self.current_statement)
            self.current_statement = None
        return self.statements

    def append_continuation_line(self, cr, line, continuation_line):
        """append a continuation line for a multiline record.
        Override and do data cleanups as necessary."""
        return line + continuation_line

    def create_statement(self, cr):
        """create a mem_bank_statement - override if you need a custom
        implementation"""
        return parserlib.BankStatement()

    def is_footer(self, cr, line):
        """determine if a line is the footer of a statement"""
        return line and bool(re.match(self.footer_regex, line))

    def is_tag(self, cr, line):
        """determine if a line has a tag"""
        return line and bool(re.match(self.tag_regex, line))

    def handle_header(self, cr, line, iterator):
        """skip header lines, create current statement"""
        for i in range(self.header_lines):
            iterator.next()
        self.current_statement = self.create_statement(cr)

    def handle_footer(self, cr, line, iterator):
        """add current statement to list, reset state"""
        self.statements.append(self.current_statement)
        self.current_statement = None

    def handle_record(self, cr, line):
        """find a function to handle the record represented by line"""
        tag_match = re.match(self.tag_regex, line)
        tag = tag_match.group(0).strip(':')
        if not hasattr(self, 'handle_tag_%s' % tag):
            logging.error('Unknown tag %s', tag)
            logging.error(line)
            return
        handler = getattr(self, 'handle_tag_%s' % tag)
        handler(cr, line[tag_match.end():])

    def handle_tag_20(self, cr, data):
        """ignore reference number"""
        pass

    def handle_tag_25(self, cr, data):
        """get account owner information"""
        self.current_statement.local_account = data

    def handle_tag_28C(self, cr, data):
        """get sequence number _within_this_batch_ - this alone
        doesn't provide a unique id!"""
        self.current_statement.id = data

    def handle_tag_60F(self, cr, data):
        """get start balance and currency"""
        self.current_statement.local_currency = data[7:10]
        self.current_statement.date = str2date(data[1:7], fmt='%y%m%d')
        self.current_statement.start_balance = \
            (1 if data[0] == 'C' else -1) * str2float(data[10:])
        self.current_statement.id = '%s/%s' % (
            self.current_statement.date.strftime('%y%m%d'),
            self.current_statement.id)

    def handle_tag_62F(self, cr, data):
        """get ending balance"""
        self.current_statement.end_balance = \
            (1 if data[0] == 'C' else -1) * str2float(data[10:])

    def handle_tag_64(self, cr, data):
        """get current balance in currency"""
        pass

    def handle_tag_65(self, cr, data):
        """get future balance in currency"""
        pass

    def handle_tag_61(self, cr, data):
        """get transaction values"""
        transaction = self.create_transaction(cr)
        self.current_statement.transactions.append(transaction)
        self.current_transaction = transaction
        transaction.execution_date = str2date(data[:6], fmt='%y%m%d')
        transaction.value_date = str2date(data[:6], fmt='%y%m%d')
        #  ...and the rest already is highly bank dependent

    def handle_tag_86(self, cr, data):
        """details for previous transaction, here most differences between
        banks occur"""
        pass

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
