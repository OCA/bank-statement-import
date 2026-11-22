# Copyright 2013-2016 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import zipfile
from io import BytesIO

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    @api.model
    def _xml_split_file(self, data_file):
        """BNP France is known to merge xml files"""
        if not data_file.startswith(b"<?xml"):
            return [data_file]
        data_file_elements = []
        all_files = data_file.split(b"<?xml")
        for file in all_files:
            if file:
                data_file_elements.append(b"<?xml" + file)
        return data_file_elements

    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        if not zipfile.is_zipfile(BytesIO(data_file)):
            parser = self.env["account.statement.import.camt.parser"]
            _logger.debug("Try parsing with camt.")
            result = []
            for data_file_element in self._xml_split_file(data_file):
                result.extend(parser.parse(data_file_element))
            return result
        else:
            try:
                with zipfile.ZipFile(BytesIO(data_file)) as data:
                    result = []
                    for member in data.namelist():
                        parsed = self._parse_file(data.open(member).read())
                        result.extend(parsed)
                return result
            # pylint: disable=except-pass
            except (zipfile.BadZipFile, ValueError):
                _logger.exception("BadZipfile exception")
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.", exc_info=True)
        return super()._parse_file(data_file)
