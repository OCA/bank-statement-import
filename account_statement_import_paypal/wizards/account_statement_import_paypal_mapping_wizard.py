# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from base64 import b64decode
from os import path

from odoo import _, api, fields, models


class AccountBankStatementImportPayPalMappingWizard(models.TransientModel):
    _name = "account.statement.import.paypal.mapping.wizard"
    _description = "Account Statement Import PayPal Mapping Wizard"
    _inherit = ["multi.step.wizard.mixin"]

    data_file = fields.Binary(
        string="PayPal Report File",
        required=True,
    )
    filename = fields.Char()
    header = fields.Char()
    date_column = fields.Char(
        string='"Date" column',
    )
    time_column = fields.Char(
        string='"Time" column',
    )
    tz_column = fields.Char(
        string='"Timezone" column',
    )
    name_column = fields.Char(
        string='"Name" column',
    )
    currency_column = fields.Char(
        string='"Currency" column',
    )
    gross_column = fields.Char(
        string='"Gross" column',
    )
    fee_column = fields.Char(
        string='"Fee" column',
    )
    balance_column = fields.Char(
        string='"Balance" column',
    )
    transaction_id_column = fields.Char(
        string='"Transaction ID" column',
    )
    description_column = fields.Char(
        string='"Description" column',
    )
    type_column = fields.Char(
        string='"Type" column',
    )
    from_email_address_column = fields.Char(
        string='"From Email Address" column',
    )
    to_email_address_column = fields.Char(
        string='"To Email Address" column',
    )
    invoice_id_column = fields.Char(
        string='"Invoice ID" column',
    )
    subject_column = fields.Char(
        string='"Subject" column',
    )
    note_column = fields.Char(
        string='"Note" column',
    )
    bank_name_column = fields.Char(
        string='"Bank Name" column',
    )
    bank_account_column = fields.Char(
        string='"Bank Account" column',
    )

    @api.onchange("data_file")
    def _onchange_data_file(self):
        Parser = self.env["account.statement.import.paypal.parser"]
        if not self.data_file:
            return
        header = Parser.parse_header(b64decode(self.data_file))
        header = [column for column in header if column]
        self.header = json.dumps(header)
        if len(header) == 22:
            self.date_column = header[0]
            self.time_column = header[1]
            self.tz_column = header[2]
            self.name_column = header[3]
            self.currency_column = header[6]
            self.gross_column = header[7]
            self.fee_column = header[8]
            self.balance_column = header[18]
            self.transaction_id_column = header[12]
            self.type_column = header[4]
            self.from_email_address_column = header[10]
            self.to_email_address_column = header[11]
            self.invoice_id_column = header[16]
            self.subject_column = header[20]
            self.note_column = header[21]
        elif len(header) == 18:
            self.date_column = header[0]
            self.time_column = header[1]
            self.tz_column = header[2]
            self.name_column = header[11]
            self.currency_column = header[4]
            self.gross_column = header[5]
            self.fee_column = header[6]
            self.balance_column = header[8]
            self.transaction_id_column = header[9]
            self.description_column = header[3]
            self.from_email_address_column = header[10]
            self.invoice_id_column = header[16]
            self.bank_name_column = header[12]
            self.bank_account_column = header[13]

    @api.model
    def statement_columns(self):
        header = self.env.context.get("header")
        if not header:
            return []
        return [(x, x) for x in json.loads(header)]

    def _get_mapping_values(self):
        """Hook for extension"""
        self.ensure_one()
        return {
            "name": _("Mapping from %s") % path.basename(self.filename),
            "float_thousands_sep": "comma",
            "float_decimal_sep": "dot",
            "date_format": "%d/%m/%Y",
            "time_format": "%H:%M:%S",
            "date_column": self.date_column,
            "time_column": self.time_column,
            "tz_column": self.tz_column,
            "name_column": self.name_column,
            "currency_column": self.currency_column,
            "gross_column": self.gross_column,
            "fee_column": self.fee_column,
            "balance_column": self.balance_column,
            "transaction_id_column": self.transaction_id_column,
            "description_column": self.description_column,
            "type_column": self.type_column,
            "from_email_address_column": self.from_email_address_column,
            "to_email_address_column": self.to_email_address_column,
            "invoice_id_column": self.invoice_id_column,
            "subject_column": self.subject_column,
            "note_column": self.note_column,
            "bank_name_column": self.bank_name_column,
            "bank_account_column": self.bank_account_column,
        }

    def import_mapping(self):
        self.ensure_one()
        mapping = self.env["account.statement.import.paypal.mapping"].create(
            self._get_mapping_values()
        )
        return {
            "type": "ir.actions.act_window",
            "name": _("Imported Mapping"),
            "res_model": "account.statement.import.paypal.mapping",
            "res_id": mapping.id,
            "view_mode": "form",
            "view_id": False,
            "target": "current",
        }
