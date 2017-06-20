# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
# © 2013-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import logging
import StringIO
import zipfile
from openerp import api, models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_camt method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        try:
            parser = self.env['account.bank.statement.import.camt.parser']
            _logger.debug("Try parsing with camt.")
            return parser.parse(data_file)
        except ValueError:
            try:
                with zipfile.ZipFile(StringIO.StringIO(data_file)) as data:
                    currency = None
                    account_number = None
                    transactions = []
                    for member in data.namelist():
                        currency, account_number, new = self._parse_file(
                            data.open(member).read()
                        )
                        transactions.extend(new)
                return currency, account_number, transactions
            except (zipfile.BadZipfile, ValueError):
                pass
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.",
                          exc_info=True)
        return super(AccountBankStatementImport, self)._parse_file(data_file)
