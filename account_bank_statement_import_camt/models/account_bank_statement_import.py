# -*- coding: utf-8 -*-
# © 2013-2017 Therp BV <http://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging

from openerp import models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_camt method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
        """Parse a CAMT053 XML file."""
        parser = self.pool['account.bank.statement.import.camt.parser']
        try:
            _logger.debug("Try parsing with camt.")
            return parser.parse(data_file)
        except ValueError:
            # Not a camt file, returning super will call next candidate:
            _logger.debug(
                "Statement file was not a camt file.", exc_info=True
            )
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)
