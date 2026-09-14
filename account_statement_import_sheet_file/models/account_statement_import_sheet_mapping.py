# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import io
from typing import Any

import xlsxwriter

from odoo import api, fields, models
from odoo.exceptions import ValidationError


class AccountStatementImportSheetMapping(models.Model):
    _name = "account.statement.import.sheet.mapping"
    _description = "Bank Statement Import Sheet Mapping"

    name = fields.Char(
        required=True,
    )
    float_thousands_sep = fields.Selection(
        string="Thousands Separator",
        selection=[
            ("dot", "dot (.)"),
            ("comma", "comma (,)"),
            ("quote", "quote (')"),
            ("none", "none"),
        ],
        default="dot",
    )
    float_decimal_sep = fields.Selection(
        string="Decimals Separator",
        selection=[("dot", "dot (.)"), ("comma", "comma (,)"), ("none", "none")],
        default="comma",
        help="When the separator is 'none', the value will be shifted according "
        "to the currency decimals. For example, 12345 will be converted to "
        "123.45",
    )
    file_encoding = fields.Selection(
        string="Encoding",
        selection=[
            ("utf-8", "UTF-8"),
            ("utf-8-sig", "UTF-8 (with BOM)"),
            ("utf-16", "UTF-16"),
            ("utf-16-sig", "UTF-16 (with BOM)"),
            ("windows-1252", "Western (Windows-1252)"),
            ("iso-8859-1", "Western (Latin-1 / ISO 8859-1)"),
            ("iso-8859-2", "Central European (Latin-2 / ISO 8859-2)"),
            ("iso-8859-4", "Baltic (Latin-4 / ISO 8859-4)"),
            ("big5", "Traditional Chinese (big5)"),
            ("gb18030", "Unified Chinese (gb18030)"),
            ("shift_jis", "Japanese (Shift JIS)"),
            ("windows-1251", "Cyrillic (Windows-1251)"),
            ("koi8_r", "Cyrillic (KOI8-R)"),
            ("koi8_u", "Cyrillic (KOI8-U)"),
        ],
        default="utf-8",
    )
    delimiter = fields.Selection(
        selection=[
            ("dot", "dot (.)"),
            ("comma", "comma (,)"),
            ("semicolon", "semicolon (;)"),
            ("tab", "tab"),
            ("space", "space"),
            ("n/a", "N/A"),
        ],
        default="comma",
    )
    quotechar = fields.Char(string="Text qualifier", size=1, default='"')
    timestamp_format = fields.Char(required=True)
    no_header = fields.Boolean(
        string="File does not contain header line",
        help="When this occurs please indicate the column number in "
        "the Columns section instead of the column name, considering "
        "that the first column is 0",
    )
    timestamp_column = fields.Char(required=True)
    currency_column = fields.Char(
        help=(
            "In case statement is multi-currency, column to get currency of "
            "transaction from"
        ),
    )
    amount_column = fields.Char(
        help="Amount of transaction in journal's currency",
    )
    amount_debit_column = fields.Char(
        string="Debit amount column",
        help="Debit amount of transaction in journal's currency",
    )
    amount_credit_column = fields.Char(
        string="Credit amount column",
        help="Credit amount of transaction in journal's currency",
    )
    amount_inverse_sign = fields.Boolean(
        string="Inverse sign of amount",
        help="In some cases such as in credit card statements the "
        "amounts are expressed in the inverse sign. "
        "By setting this flag during the upload the amounts "
        "will be inverted in sign.",
    )
    balance_column = fields.Char(
        help="Balance after transaction in journal's currency",
    )
    original_currency_column = fields.Char(
        help=(
            "In case statement provides original currency for transactions "
            "with automatic currency conversion, column to get original "
            "currency of transaction from"
        ),
    )
    original_amount_column = fields.Char(
        help=(
            "In case statement provides original currency for transactions "
            "with automatic currency conversion, column to get original "
            "transaction amount in original transaction currency from"
        ),
    )
    amount_type = fields.Selection(
        selection=[
            ("simple_value", "Simple value"),
            ("absolute_value", "Absolute value"),
            ("distinct_credit_debit", "Distinct Credit/debit Column"),
        ],
        string="Amount type",
        required=True,
        default="simple_value",
        help=(
            "Simple value: use igned amount in amount column\n"
            "Absolute Value: use a same column for debit and credit\n"
            "(absolute value + indicate sign)\n"
            "Distinct Credit/debit Column: use a distinct column for debit and credit"
        ),
    )
    amount_column = fields.Char(
        string="Amount column",
        help=(
            'Used if amount type is "Simple value" or "Absolute value"\n'
            "Amount of transaction in journal's currency\n"
            "Some statement formats use credit/debit columns"
        ),
    )
    debit_credit_column = fields.Char(
        string="Debit/credit column",
        help=(
            'Used if amount type is "Absolute value"\n'
            "Some statement formats use absolute amount value and indicate sign\n"
            "of the transaction by specifying if it was a debit or a credit one"
        ),
    )
    debit_value = fields.Char(
        help="Value of debit/credit column that indicates if it's a debit",
        default="D",
    )
    credit_value = fields.Char(
        help="Value of debit/credit column that indicates if it's a credit",
        default="C",
    )
    transaction_id_column = fields.Char(
        string="Unique transaction ID column",
    )
    description_column = fields.Char()
    notes_column = fields.Char()
    reference_column = fields.Char()
    partner_name_column = fields.Char()
    bank_name_column = fields.Char(
        help="Partner's bank",
    )
    bank_account_column = fields.Char(
        help="Partner's bank account",
    )
    footer_lines_skip_count = fields.Integer(
        string="Footer lines skip count",
        help="Set the Footer lines number."
        "Used in some csv/xlsx file that integrate meta data in"
        "last lines.",
        default="0",
    )
    header_lines_skip_count = fields.Integer(
        string="Header lines skip count",
        help="Set the Header lines number.",
        default="0",
    )
    skip_empty_lines = fields.Boolean(
        default=True,
        help="Allows to skip empty lines",
    )
    offset_column = fields.Integer(
        default=0,
        help="Columns to ignore before starting to parse",
    )
    template_datas = fields.Binary(string="Template File", readonly=True)
    template_fname = fields.Char(string="Template File Name", readonly=True)

    def _get_template_columns(self) -> list[dict]:
        self.ensure_one()
        columns = []
        if self.transaction_id_column:
            columns += [
                {"header": self.transaction_id_column, "type": "text", "width": 18}
            ]

        if self.timestamp_column:
            columns += [
                {"header": self.timestamp_column, "type": "datetime", "width": 15}
            ]

        if self.partner_name_column:
            columns += [
                {"header": self.partner_name_column, "type": "text", "width": 30}
            ]

        if self.description_column:
            columns += [
                {"header": self.description_column, "type": "text", "width": 60}
            ]

        if self.reference_column:
            columns += [{"header": self.reference_column, "type": "text", "width": 18}]

        if self.amount_type == "simple_value":
            columns += [{"header": self.amount_column, "type": "float", "width": 15}]
        elif self.amount_type == "absolute_value":
            columns.append(
                {"header": self.debit_credit_column, "type": "float", "width": 15}
            )
        else:
            columns += [
                {"header": self.amount_debit_column, "type": "float", "width": 15},
                {"header": self.amount_credit_column, "type": "float", "width": 15},
            ]

        if self.currency_column:
            columns += [{"header": self.currency_column, "type": "text", "width": 15}]

        if self.original_currency_column:
            columns += [
                {"header": self.original_currency_column, "type": "text", "width": 18}
            ]

        if self.original_amount_column:
            columns += [
                {"header": self.original_amount_column, "type": "float", "width": 15}
            ]

        if self.balance_column:
            columns += [{"header": self.balance_column, "type": "float", "width": 15}]

        if self.notes_column:
            columns += [{"header": self.notes_column, "type": "text", "width": 15}]

        if self.bank_name_column:
            columns += [{"header": self.bank_name_column, "type": "text", "width": 15}]

        if self.bank_account_column:
            columns += [
                {"header": self.bank_account_column, "type": "text", "width": 15}
            ]
        return columns

    def generate_xlsx_template(self) -> None:
        self.ensure_one()
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {"in_memory": True})
        worksheet = workbook.add_worksheet("Sheet1")

        # Formats
        header_format = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "align": "center",
                "font_size": 12,
            }
        )

        float_format = workbook.add_format(
            {
                "align": "right",
                "font_size": 11,
            }
        )

        datetime_format = workbook.add_format(
            {
                "align": "right",
                "font_size": 11,
            }
        )

        text_format = workbook.add_format(
            {
                "align": "left",
                "font_size": 11,
            }
        )

        # Define columns
        columns = self._get_template_columns()

        # Write headers
        for col_idx, col in enumerate(columns):
            if col["type"] == "float":
                worksheet.set_column(col_idx, col_idx, col["width"], float_format)
            elif col["type"] == "datetime":
                worksheet.set_column(col_idx, col_idx, col["width"], datetime_format)
            else:
                worksheet.set_column(col_idx, col_idx, col["width"], text_format)
            worksheet.write(0, col_idx, col["header"], header_format)

        workbook.close()
        output.seek(0)

        self.write(
            {
                "template_datas": base64.b64encode(output.read()),
                "template_fname": f"{self.name}.xlsx",
            }
        )
        output.close()

    def download_xlsx_template(self) -> dict | bool:
        self.ensure_one()
        self.generate_xlsx_template()
        if not self.template_datas:
            return False
        return {
            "type": "ir.actions.act_url",
            "url": (
                f"/web/content/?model={self._name}"
                f"&id={self.id}"
                f"&field=template_datas"
                f"&filename={self.template_fname}"
                f"&download=true"
            ),
            "target": "self",
        }

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> Any:
        res = super().create(vals_list)
        for rec in res:
            rec.generate_xlsx_template()
        return res

    def write(self, vals: dict) -> bool:
        res = super().write(vals)
        if not vals.get("template_datas") and not vals.get("template_fname"):
            for rec in self:
                rec.generate_xlsx_template()
        return res

    @api.constrains(
        "amount_type",
        "amount_column",
        "debit_credit_column",
        "amount_debit_column",
        "amount_credit_column",
    )
    def _check_amount_type(self):
        for item in self:
            if item.amount_type == "simple_value" and not item.amount_column:
                raise ValidationError(
                    self.env._(
                        "Use amount_column if you have set Amount type = 'Single value'"
                    )
                )
            elif item.amount_type == "absolute_value" and not item.debit_credit_column:
                raise ValidationError(
                    self.env._(
                        "Use debit_credit_column if you have set "
                        "Amount type = 'Absolute value'"
                    )
                )
            elif item.amount_type == "distinct_credit_debit" and (
                not item.amount_debit_column or not item.amount_credit_column
            ):
                raise ValidationError(
                    self.env._(
                        "Use amount_debit_column and amount_credit_column if you "
                        "have set Amount type = 'Distinct Credit/debit Column'"
                    )
                )

    @api.onchange("float_thousands_sep")
    def onchange_thousands_separator(self):
        if "dot" == self.float_thousands_sep == self.float_decimal_sep:
            self.float_decimal_sep = "comma"
        elif "comma" == self.float_thousands_sep == self.float_decimal_sep:
            self.float_decimal_sep = "dot"

    @api.onchange("float_decimal_sep")
    def onchange_decimal_separator(self):
        if "dot" == self.float_thousands_sep == self.float_decimal_sep:
            self.float_thousands_sep = "comma"
        elif "comma" == self.float_thousands_sep == self.float_decimal_sep:
            self.float_thousands_sep = "dot"

    @api.constrains("offset_column")
    def _check_columns(self):
        for mapping in self:
            if mapping.offset_column < 0:
                raise ValidationError(self.env._("Offsets cannot be negative"))

    def _get_float_separators(self):
        self.ensure_one()
        separators = {
            "dot": ".",
            "comma": ",",
            "quote": "'",
            "none": "",
        }
        return (
            separators[self.float_thousands_sep],
            separators[self.float_decimal_sep],
        )

    @api.model
    def _decode_column_delimiter_character(self, delimiter):
        return (
            {"dot": ".", "comma": ",", "semicolon": ";", "tab": "\t", "space": " "}
        ).get(delimiter)

    def _get_column_delimiter_character(self):
        return self._decode_column_delimiter_character(self.delimiter)
