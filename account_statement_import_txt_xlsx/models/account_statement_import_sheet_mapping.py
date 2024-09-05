# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountStatementImportSheetMapping(models.Model):
    _name = "account.statement.import.sheet.mapping"
    _description = "Bank Statement Import Sheet Mapping"

    name = fields.Char(
        required=True,
    )
    float_thousands_sep = fields.Selection(
        string="Thousands Separator",
        selection=[("dot", "dot (.)"), ("comma", "comma (,)"), ("none", "none")],
        default="dot",
    )
    float_decimal_sep = fields.Selection(
        string="Decimals Separator",
        selection=[("dot", "dot (.)"), ("comma", "comma (,)"), ("none", "none")],
        default="comma",
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
        string="Delimiter",
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
    timestamp_format = fields.Char(string="Timestamp Format", required=True)
    no_header = fields.Boolean(
        "File does not contain header line",
        help="When this occurs please indicate the column number in the Columns section "
        "instead of the column name, considering that the first column is 0",
    )
    offset_header = fields.Integer(
        "Offset Header",
        default=0,
        help="Number of row to ignore until the header",
    )
    skip_empty_lines = fields.Boolean(
        "Skip Empty Lines",
        default=False,
        help="Allows to skip empty lines",
    )
    offset_column = fields.Integer(
        "Offset Column",
        default=0,
        help="Horizontal spaces to ignore before starting to parse",
    )
    offset_row = fields.Integer(
        "Offset Row",
        default=0,
        help="Vertical spaces to ignore before starting to parse",
    )
    timestamp_column = fields.Char(string="Timestamp column", required=True)
    currency_column = fields.Char(
        string="Currency column",
        help=(
            "In case statement is multi-currency, column to get currency of "
            "transaction from"
        ),
    )
    amount_column = fields.Char(
        string="Amount column",
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
    balance_column = fields.Char(
        string="Balance column",
        help="Balance after transaction in journal's currency",
    )
    original_currency_column = fields.Char(
        string="Original currency column",
        help=(
            "In case statement provides original currency for transactions "
            "with automatic currency conversion, column to get original "
            "currency of transaction from"
        ),
    )
    original_amount_column = fields.Char(
        string="Original amount column",
        help=(
            "In case statement provides original currency for transactions "
            "with automatic currency conversion, column to get original "
            "transaction amount in original transaction currency from"
        ),
    )
    debit_credit_column = fields.Char(
        string="Debit/credit column",
        help=(
            "Some statement formats use absolute amount value and indicate sign"
            "of the transaction by specifying if it was a debit or a credit one"
        ),
    )
    debit_value = fields.Char(
        string="Debit value",
        help="Value of debit/credit column that indicates if it's a debit",
        default="D",
    )
    credit_value = fields.Char(
        string="Credit value",
        help="Value of debit/credit column that indicates if it's a credit",
        default="C",
    )
    transaction_id_column = fields.Char(
        string="Unique transaction ID column",
    )
    description_column = fields.Char(
        string="Description column",
    )
    notes_column = fields.Char(
        string="Notes column",
    )
    reference_column = fields.Char(
        string="Reference column",
    )
    partner_name_column = fields.Char(
        string="Partner Name column",
    )
    bank_name_column = fields.Char(
        string="Bank Name column",
        help="Partner's bank",
    )
    bank_account_column = fields.Char(
        string="Bank Account column",
        help="Partner's bank account",
    )

    _sql_constraints = [
        (
            "check_amount_columns",
            (
                "CHECK("
                "amount_column IS NULL "
                "OR (amount_debit_column IS NULL AND amount_credit_column IS NULL)"
                ")"
            ),
            "Use amount_column OR (amount_debit_column AND amount_credit_column).",
        ),
    ]

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

    @api.constrains("offset_column", "offset_row")
    def _check_columns(self):
        for mapping in self:
            if mapping.offset_column < 0 or mapping.offset_row < 0:
                raise ValidationError(_("Offsets cannot be negative"))

    def _get_float_separators(self):
        self.ensure_one()
        separators = {
            "dot": ".",
            "comma": ",",
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
