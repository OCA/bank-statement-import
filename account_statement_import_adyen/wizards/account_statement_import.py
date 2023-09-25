# Copyright 2017 Opener BV (<https://opener.amsterdam>)
# Copyright 2021-2023 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Add import of Adyen statements."""
# pylint: disable=protected-access,no-self-use
import logging

from odoo import _, models

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


class AccountStatementImport(models.TransientModel):
    """Add import of Adyen statements."""

    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        """Parse an Adyen xlsx file and map merchant account strings to journals."""
        try:
            return self._parse_adyen_file(data_file)
        except Exception as exc:  # pylint: disable=broad-except
            message = (
                _("Statement file %s was not a Adyen settlement details file.")
                % self.statement_filename
                or "* no filename *"
            )
            if self.env.context.get("account_statement_import_adyen", False):
                raise ValueError(message) from exc
            _logger.debug(message, exc_info=True)
            return super()._parse_file(data_file)

    def _parse_adyen_file(self, data_file):
        """Just parse the adyen file."""
        _logger.debug(_("Try parsing as Adyen settlement details."))
        parser = self.env["account.statement.import.adyen.parser"]
        rows = self._get_rows(data_file)
        return parser.parse_rows(rows)

    def _get_rows(self, data_file):
        """Get rows from data_file."""
        # Try to use original import file name.
        filename = (
            self.statement_filename
            if self.statement_filename
            else "Ayden settlement details"
        )
        import_model = self.env["base_import.import"]
        importer = import_model.create(
            {
                "file": data_file,
                "file_name": filename,
            }
        )
        _num_rows, rows = importer._read_file({"quoting": '"', "separator": ","})
        return rows
