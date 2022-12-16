# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


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
        help="When this occurs please indicate the column number in the Columns section "
        "instead of the column name, considering that the first column is 0",
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
    debit_credit_column = fields.Char(
        string="Debit/credit column",
        help=(
            "Some statement formats use absolute amount value and indicate sign"
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
