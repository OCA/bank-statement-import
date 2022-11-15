# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from base64 import b64decode
from os import path

from odoo import _, api, fields, models


class AccountStatementImportSheetMappingWizard(models.TransientModel):
    _name = "account.statement.import.sheet.mapping.wizard"
    _description = "Bank Statement Import Sheet Mapping Wizard"
    _inherit = ["multi.step.wizard.mixin"]

    attachment_ids = fields.Many2many(
        comodel_name="ir.attachment",
        string="Files",
        required=True,
        relation="account_statement_import_sheet_mapping_wiz_attachment_rel",
    )
    column_labels_row = fields.Integer(
        string="Header line",
        help="The number of line that contan column names.\n"
        "Used if csv/xls files contain\n"
        "meta data in first lines\n ",
        default="1",
    )
    header = fields.Char()
    file_encoding = fields.Selection(
        string="Encoding",
        selection=lambda self: self._selection_file_encoding(),
    )
    delimiter = fields.Selection(
        selection=lambda self: self._selection_delimiter(),
    )
    quotechar = fields.Char(
        string="Text qualifier",
        size=1,
    )
    timestamp_column = fields.Char()
    currency_column = fields.Char(
        help=(
            "In case statement is multi-currency, column to get currency of "
            "transaction from"
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
            "Simple value: use igned amount in ammount comlumn\n"
            "Absolute Value: use a same comlumn for debit and credit\n"
            "(absolute value + indicate sign)\n"
            "Distinct Credit/debit Column: use a distinct comlumn for debit and credit"
        ),
    )
    amount_column = fields.Char(
        help="Amount of transaction in journal's currency",
    )
    amount_debit_column = fields.Char(
        related="debit_column", store=True, string="OCA Debit colum"
    )
    amount_credit_column = fields.Boolean(
        related="credit_column", store=True, string="OCA Credit colum"
    )
    debit_column = fields.Char(
        string="Debit amount column",
        help="Debit amount of transaction in journal's currency"
        "Used if amount type is 'Distinct Credit/debit Column'",
    )
    credit_column = fields.Boolean(
        string="Credit column",
        help="Credit amount of transaction in journal's currency"
        "Used if amount type is 'Distinct Credit/debit Column'",
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

    @api.model
    def _selection_file_encoding(self):
        return (
            self.env["account.statement.import.sheet.mapping"]
            ._fields["file_encoding"]
            .selection
        )

    @api.model
    def _selection_delimiter(self):
        return (
            self.env["account.statement.import.sheet.mapping"]
            ._fields["delimiter"]
            .selection
        )

    @api.onchange("attachment_ids")
    def _onchange_attachment_ids(self):
        Parser = self.env["account.statement.import.sheet.parser"]
        Mapping = self.env["account.statement.import.sheet.mapping"]
        if not self.attachment_ids:
            return
        csv_options = {}
        if self.delimiter:
            csv_options["delimiter"] = Mapping._decode_column_delimiter_character(
                self.delimiter
            )
        if self.quotechar:
            csv_options["quotechar"] = self.quotechar
        header = []
        for data_file in self.attachment_ids:
            header += Parser.parse_header(
                b64decode(data_file.datas),
                self.file_encoding,
                csv_options,
                self.column_labels_row,
            )
        header = list(set(header))
        self.header = json.dumps(header)

    @api.model
    def statement_columns(self):
        header = self.env.context.get("header")
        if not header:
            return []
        return [(x, x) for x in json.loads(header)]

    def _get_mapping_values(self):
        """Hook for extension"""
        self.ensure_one()
        filename = "& ".join(self.attachment_ids.mapped("name"))
        return {
            "name": _("Mapping from %s") % path.basename(filename),
            "float_thousands_sep": "comma",
            "float_decimal_sep": "dot",
            "file_encoding": self.file_encoding,
            "delimiter": self.delimiter,
            "quotechar": self.quotechar,
            "timestamp_format": "%d/%m/%Y",
            "timestamp_column": self.timestamp_column,
            "currency_column": self.currency_column,
            "amount_type": self.amount_type,
            "debit_column": self.debit_column,
            "credit_column": self.credit_column,
            "amount_column": self.amount_column,
            "balance_column": self.balance_column,
            "original_currency_column": self.original_currency_column,
            "original_amount_column": self.original_amount_column,
            "debit_credit_column": self.debit_credit_column,
            "debit_value": self.debit_value,
            "credit_value": self.credit_value,
            "transaction_id_column": self.transaction_id_column,
            "description_column": self.description_column,
            "notes_column": self.notes_column,
            "reference_column": self.reference_column,
            "partner_name_column": self.partner_name_column,
            "bank_name_column": self.bank_name_column,
            "bank_account_column": self.bank_account_column,
        }

    def import_mapping(self):
        self.ensure_one()
        mapping = self.env["account.statement.import.sheet.mapping"].create(
            self._get_mapping_values()
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Mapping"),
            "res_model": "account.statement.import.sheet.mapping",
            "res_id": mapping.id,
            "view_mode": "form",
            "view_id": False,
            "target": "current",
        }
