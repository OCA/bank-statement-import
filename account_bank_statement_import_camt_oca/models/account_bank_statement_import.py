# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
from io import BytesIO
import zipfile
from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
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
                with zipfile.ZipFile(BytesIO(data_file)) as data:
                    currency = None
                    account_number = None
                    transactions = []
                    for member in data.namelist():
                        currency, account_number, new = self._parse_file(
                            data.open(member).read()
                        )
                        transactions.extend(new)
                return currency, account_number, transactions
            except (zipfile.BadZipFile, ValueError):
                pass
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.",
                          exc_info=True)
        return super(AccountBankStatementImport, self)._parse_file(data_file)
