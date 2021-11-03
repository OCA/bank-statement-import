# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import zipfile
from io import BytesIO

from odoo import models
from odoo.exceptions import ValidationError

from .res_config_settings import CHECKING_NAME_UNIQUE

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        try:
            parser = self.env["account.statement.import.camt.parser"]
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
            _logger.debug("Statement file was not a camt file.", exc_info=True)
        return super()._parse_file(data_file)

    def _check_parsed_data(self, stmts_vals):
        """Check for unique statement name if config param is set."""
        result = super()._check_parsed_data(stmts_vals)
        config_param = self.env["ir.config_parameter"].sudo()
        checking_name_unique = config_param.get_param(CHECKING_NAME_UNIQUE, False)
        if not result or not checking_name_unique:
            return result

        def raise_error(message):
            raise ValidationError(message + ", ".join(dup_names))

        names = [v["name"] for v in stmts_vals]
        name_set = set(names)
        dup_names = {name for name in name_set if names.count(name) > 1}
        if dup_names:
            raise_error("Duplicated name in data file itself: ")

        domain = [("name", "in", list(name_set))]
        dup_records = self.env["account.bank.statement"].search(domain)
        dup_names.update(dup_records.mapped("name"))
        if dup_names:
            raise_error("Bank statement must be unique: ")
        return result
