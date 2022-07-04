# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    @api.model
    def _convert_line_to_transactions(self, line):
        res = super()._convert_line_to_transactions(line)
        transaction = res[0]
        check_number = line.get("check_number")
        if check_number:
            transaction["check_number"] = check_number
        return [transaction]

    def _get_data_columns(self, header, mapping):
        columns = super()._get_data_columns(header, mapping)
        columns.update(
            {
                "check_number_column": header.index(mapping.check_number_column) if mapping.check_number_column else None
            }
        )
        return columns

    def _get_data_line(self, mapping, columns, values):
        line = super()._get_data_line(mapping, columns, values)
        check_number = (
            values[columns["check_number_column"]]
            if columns["check_number_column"] is not None
            else None
        )
        if check_number is not None:
            line["check_number"] = check_number
        return line
