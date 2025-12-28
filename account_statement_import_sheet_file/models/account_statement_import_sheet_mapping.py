# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import re
from io import BytesIO

from PyPDF2 import PdfReader

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import (
    safe_eval,
    test_python_expr,
)


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

    DEFAULT_PYTHON_CODE = (
        "# Available variables:\n"
        "#  - data_file: the data to preprocess\n"
        "#  - match: re.match regex Python library\n"
        "#\n"
        "# update data_file so that it can be parsed as a string in a csv format\n"
    )

    preprocessor_code = fields.Text(
        string="Python Code",
        groups="base.group_system",
        default=DEFAULT_PYTHON_CODE,
        help="Write Python code to pre-process a file like converting a pdf to csv.",
    )

    @api.constrains("preprocessor_code")
    def _check_python_code(self):
        for action in self.sudo().filtered("preprocessor_code"):
            msg = test_python_expr(expr=action.preprocessor_code.strip(), mode="exec")
            if msg:
                raise ValidationError(msg)

    def _eval_code(self, data_file):
        code = self.sudo().preprocessor_code
        expr = code.strip()
        eval_context = {
            "match": re.match,
            "data_file": data_file,
        }
        try:
            safe_eval(expr, eval_context, mode="exec", nocopy=True)
        except Exception as err:
            raise UserError(
                self.env._(
                    "Error when evaluating the preprocessor code:"
                    "\n %(name)s \n(%(error)s)",
                    name=self.name,
                    error=err,
                )
            ) from err
        return eval_context.get("data_file", data_file)

    def _preprocess(self, data_file):
        self.ensure_one()
        if data_file[:4] == b"%PDF":
            data_file = PdfReader(BytesIO(data_file))
        data_file = self._eval_code(data_file)
        return data_file

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
