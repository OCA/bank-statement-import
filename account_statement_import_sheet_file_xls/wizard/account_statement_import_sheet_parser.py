# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# Copyright 2026 Andrii Kompaniiets - Tecnativa
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import xlrd
from xlrd import xldate_as_datetime

from odoo import api, models


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _get_mimetype_sheet_type_map(self):
        """Return supported MIME types and their parser suffixes."""
        mimetype_sheet_type_map = super()._get_mimetype_sheet_type_map()
        mimetype_sheet_type_map.update(
            {
                "application/vnd.ms-excel": "xls",
            }
        )
        return mimetype_sheet_type_map

    @api.model
    def parse_header_xls(self, rows, mapping):
        """
        Return the XLS header row after applying configured skips and offset.
        """
        if mapping.no_header:
            return []
        header_line = mapping.header_lines_skip_count
        # prevent negative indexes
        if header_line > 0:
            header_line -= 1
        header = [str(value).strip() for value in rows[1].row_values(header_line)]
        if mapping.offset_column:
            header = header[mapping.offset_column :]
        return header

    def _parse_lines_xls(self, mapping, data_file, currency_code):
        """Parse XLS content into normalized statement line dictionaries.
        :return: Parsed statement lines ready for transaction conversion.
        """
        columns = dict()
        workbook = xlrd.open_workbook(
            file_contents=data_file,
            encoding_override=(
                mapping.file_encoding if mapping.file_encoding else None
            ),
        )
        xls = (
            workbook,
            workbook.sheet_by_index(0),
        )
        header = self.parse_header_xls(xls, mapping)
        numrows = xls[1].nrows
        for column_name in self._get_column_names():
            columns[column_name] = self._get_column_indexes(
                header, column_name, mapping
            )

        label_line = mapping.header_lines_skip_count
        footer_line = numrows - mapping.footer_lines_skip_count
        rows = range(label_line, footer_line)
        rows_values = self._get_xls_row_values(mapping, xls, rows, label_line)
        data = rows_values, label_line, footer_line
        return self._parse_rows(mapping, currency_code, data, columns)

    def _get_xls_row_values(self, mapping, xls, rows, label_line):
        """Return row values from an XLS sheet with date cells normalized."""
        parsed_rows = []
        for _, row in enumerate(rows, label_line):
            book = xls[0]
            sheet = xls[1]
            values = []
            for col_index in range(mapping.offset_column, sheet.row_len(row)):
                cell_type = sheet.cell_type(row, col_index)
                cell_value = sheet.cell_value(row, col_index)
                if cell_type == xlrd.XL_CELL_DATE:
                    cell_value = xldate_as_datetime(cell_value, book.datemode)
                values.append(cell_value)
            parsed_rows.append(values)
        return parsed_rows
