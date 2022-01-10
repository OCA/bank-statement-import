# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import zipfile
from io import BytesIO

from odoo import models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        """Parse a MRX XML file."""
        #try:
        parser = self.env["account.statement.import.mrx.parser"]
        _logger.warning("Try parsing with six parser.")
        
       
        try:
            a = 1
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
            # Not a mrx file, returning super will call next candidate:
        _logger.warning("Statement file was not a merchantReconciliationXML (MRX) file.", exc_info=True)
        return super()._parse_file(data_file)
