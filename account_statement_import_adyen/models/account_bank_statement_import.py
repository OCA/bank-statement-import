# Copyright 2017 Opener BV (<https://opener.amsterdam>)
# Copyright 2021-2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Add import of Adyen statements."""
# pylint: disable=protected-access,no-self-use
import logging

from odoo import _, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class AccountBankStatementImport(models.TransientModel):
    """Add import of Adyen statements."""

    _inherit = "account.bank.statement.import"

    def _parse_file(self, data_file):
        """Parse an Adyen xlsx file and map merchant account strings to journals."""
        try:
            return self._parse_adyen_file(data_file)
        except Exception as exc:  # pylint: disable=broad-except
            message = _("Statement file was not a Adyen settlement details file.")
            if self.env.context.get("account_bank_statement_import_adyen", False):
                raise UserError(message) from exc
            _logger.debug(message, exc_info=True)
            return super()._parse_file(data_file)

    def _parse_adyen_file(self, data_file):
        """Just parse the adyen file."""
        _logger.debug(_("Try parsing as Adyen settlement details."))
        parser = self.env["account.bank.statement.import.adyen.parser"]
        rows = self._get_rows(data_file)
        return parser.parse_rows(rows)

    def _get_rows(self, data_file):
        """Get rows from data_file."""
        # Try to use original import file name.
        filename = (
            self.attachment_ids[0].name
            if len(self.attachment_ids) == 1
            else "Ayden settlement details"
        )
        import_model = self.env["base_import.import"]
        importer = import_model.create({"file": data_file, "file_name": filename})
        return importer._read_file({"quoting": '"', "separator": ","})
