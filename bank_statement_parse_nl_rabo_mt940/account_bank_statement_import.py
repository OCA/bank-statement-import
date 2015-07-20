# -*- coding: utf-8 -*-
"""Parse a MT940 RABO file."""
##############################################################################
#
#    Copyright (C) 2013-2015 Therp BV <http://therp.nl>
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
import logging

from openerp import models
from .mt940 import MT940Parser as Parser


_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add parsing of RABO mt940 files to bank statement import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
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
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)
