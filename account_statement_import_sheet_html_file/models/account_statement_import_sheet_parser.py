# Copyright 2026 Simone Rubino
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from csv import writer
from io import StringIO

from lxml import etree

from odoo import models

_logger = logging.getLogger(__name__)


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _get_data_parsers(self):
        parsers = super()._get_data_parsers()
        parsers = [self._parse_data_html] + parsers
        return parsers

    def _parse_data_html(self, mapping, data_file):
        decoded_file = self._decode_data_file(data_file, encoding=mapping.file_encoding)
        is_html = decoded_file.lower().lstrip().startswith("<html>")
        if is_html:
            # Convert to CSV
            rows = etree.HTML(decoded_file).xpath("//table//tr")

            csv_content_stream = StringIO()
            csv_options = self._get_csv_options(mapping)
            wr = writer(csv_content_stream, **csv_options)
            wr.writerow([col.text for col in rows[0].xpath(".//th")])
            wr.writerows([[col.text for col in row.xpath(".//td")] for row in rows[1:]])
            decoded_file = csv_content_stream.getvalue()

            # Parse as CSV
            encoded_file = decoded_file.encode(mapping.file_encoding)
            parsed_data = self._parse_data_csv(mapping, encoded_file)
        else:
            parsed_data = None
        return parsed_data
