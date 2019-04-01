# -*- coding: utf-8 -*-
# Copyright 2019 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import re
from odoo import api, models
from odoo.addons.account_bank_statement_import_mt940_base.mt940 import\
    MT940, str2amount, get_subfields


_logger = logging.getLogger(__name__)


class MollieMT940(MT940):

    tag_61_regex = re.compile(
        r'^(?P<date>\d{6})(?P<date2>\d{4})(?P<sign>[CD])(?P<amount>\d+,\d{2})N'
        r'(?P<type>.{3})'
    )

    def __init__(self):
        super(MollieMT940, self).__init__()
        self.mt940_type = 'Mollie'
        self.header_regex = '^:20:940'
        self.header_lines = 0

    def pre_process_data(self, data):
        return [(data or '').replace('\r\n', '\n')]

    def is_mt940_statement(self, line):
        if not line.startswith(':20:940'):
            raise ValueError()

    def handle_tag_61(self, data):
        """Handle tag 61: transaction data."""
        super(MollieMT940, self).handle_tag_61(data)
        parsed_data = self.tag_61_regex.match(data).groupdict()
        self.current_transaction['amount'] = str2amount(
            parsed_data['sign'], parsed_data['amount'],
        )

    def handle_tag_86(self, data):
        """Handle tag 86: transaction details"""
        if not self.current_transaction:
            return
        codewords = ['TRTP', 'IBAN', 'BIC', 'NAME', 'REMI', 'EREF']
        subfields = get_subfields(data, codewords)
        self.current_transaction['account_number'] = ''.join(
            subfields.get('IBAN', [])
        )
        self.current_transaction['partner_name'] = ''.join(
            subfields.get('NAME', [])
        )
        self.current_transaction['name'] = ''.join(
            subfields.get('REMI', [])
        )
        eref = ''.join(subfields.get('EREF', []))
        if eref != 'NOTPROVIDED':
            self.current_transaction['ref'] = eref


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        try:
            _logger.debug('Try parsing as Mollie MT940 file')
            return MollieMT940().parse(data_file)
        except ValueError:
            _logger.debug('Statement file was not a Mollie MT940 file')
        return super(AccountBankStatementImport, self)._parse_file(data_file)
