# -*- coding: utf-8 -*-
# Copyright 2013-2018 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from openerp import api, models

from .mt940 import MT940Parser as Parser


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add parsing of RABO mt940 files to bank statement import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a MT940 RABO file."""
        parser = Parser()
        try:
            _logger.debug("Try parsing with MT940 RABO.")
            statements = parser.parse(data_file)
            return statements
        except ValueError:
            # Returning super will call next candidate:
            _logger.debug("Statement file was not a MT940 RABO file.",
                          exc_info=True)
            return super(
                AccountBankStatementImport, self)._parse_file(data_file)
