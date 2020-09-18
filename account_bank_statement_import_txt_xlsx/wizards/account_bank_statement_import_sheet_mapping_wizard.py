# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _

from base64 import b64decode
import json
from os import path


class AccountBankStatementImportSheetMappingWizard(models.TransientModel):
    _name = 'account.bank.statement.import.sheet.mapping.wizard'
    _description = 'Account Bank Statement Import Sheet Mapping Wizard'
    _inherit = ['multi.step.wizard.mixin']

    data_file = fields.Binary(
        string='Bank Statement File',
        required=True,
    )
    filename = fields.Char()
    header = fields.Char()
    file_encoding = fields.Selection(
        string='Encoding',
        selection=lambda self: self._selection_file_encoding(),
    )
    delimiter = fields.Selection(
        string='Delimiter',
        selection=lambda self: self._selection_delimiter(),
    )
    quotechar = fields.Char(
        string='Text qualifier',
        size=1,
    )
    timestamp_column = fields.Char(
        string='Timestamp column',
    )
    currency_column = fields.Char(
        string='Currency column',
        help=(
            'In case statement is multi-currency, column to get currency of '
            'transaction from'
        ),
    )
    amount_column = fields.Char(
        string='Amount column',
        help='Amount of transaction in journal\'s currency',
    )
    balance_column = fields.Char(
        string='Balance column',
        help='Balance after transaction in journal\'s currency',
    )
    original_currency_column = fields.Char(
        string='Original currency column',
        help=(
            'In case statement provides original currency for transactions '
            'with automatic currency conversion, column to get original '
            'currency of transaction from'
        ),
    )
    original_amount_column = fields.Char(
        string='Original amount column',
        help=(
            'In case statement provides original currency for transactions '
            'with automatic currency conversion, column to get original '
            'transaction amount in original transaction currency from'
        ),
    )
    debit_credit_column = fields.Char(
        string='Debit/credit column',
        help=(
            'Some statement formats use absolute amount value and indicate sign'
            'of the transaction by specifying if it was a debit or a credit one'
        ),
    )
    debit_value = fields.Char(
        string='Debit value',
        help='Value of debit/credit column that indicates if it\'s a debit',
        default='D',
    )
    credit_value = fields.Char(
        string='Credit value',
        help='Value of debit/credit column that indicates if it\'s a credit',
        default='C',
    )
    transaction_id_column = fields.Char(
        string='Unique transaction ID column',
    )
    description_column = fields.Char(
        string='Description column',
    )
    notes_column = fields.Char(
        string='Notes column',
    )
    reference_column = fields.Char(
        string='Reference column',
    )
    partner_name_column = fields.Char(
        string='Partner Name column',
    )
    bank_name_column = fields.Char(
        string='Bank Name column',
        help='Partner\'s bank',
    )
    bank_account_column = fields.Char(
        string='Bank Account column',
        help='Partner\'s bank account',
    )

    @api.model
    def _selection_file_encoding(self):
        return self.env['account.bank.statement.import.sheet.mapping']._fields[
            'file_encoding'
        ].selection

    @api.model
    def _selection_delimiter(self):
        return self.env['account.bank.statement.import.sheet.mapping']._fields[
            'delimiter'
        ].selection

    @api.onchange('data_file')
    def _onchange_data_file(self):
        Parser = self.env['account.bank.statement.import.sheet.parser']
        Mapping = self.env['account.bank.statement.import.sheet.mapping']
        if not self.data_file:
            return
        csv_options = {}
        if self.delimiter:
            csv_options['delimiter'] = \
                Mapping._decode_column_delimiter_character(self.delimiter)
        if self.quotechar:
            csv_options['quotechar'] = self.quotechar
        header = Parser.parse_header(
            b64decode(self.data_file),
            self.file_encoding,
            csv_options
        )
        self.header = json.dumps(header)

    @api.model
    def statement_columns(self):
        header = self.env.context.get('header')
        if not header:
            return []
        return [(x, x) for x in json.loads(header)]

    @api.multi
    def _get_mapping_values(self):
        """Hook for extension"""
        self.ensure_one()
        return {
            'name': _('Mapping from %s') % path.basename(self.filename),
            'float_thousands_sep': 'comma',
            'float_decimal_sep': 'dot',
            'file_encoding': self.file_encoding,
            'delimiter': self.delimiter,
            'quotechar': self.quotechar,
            'timestamp_format': '%d/%m/%Y',
            'timestamp_column': self.timestamp_column,
            'currency_column': self.currency_column,
            'amount_column': self.amount_column,
            'balance_column': self.balance_column,
            'original_currency_column': self.original_currency_column,
            'original_amount_column': self.original_amount_column,
            'debit_credit_column': self.debit_credit_column,
            'debit_value': self.debit_value,
            'credit_value': self.credit_value,
            'transaction_id_column': self.transaction_id_column,
            'description_column': self.description_column,
            'notes_column': self.notes_column,
            'reference_column': self.reference_column,
            'partner_name_column': self.partner_name_column,
            'bank_name_column': self.bank_name_column,
            'bank_account_column': self.bank_account_column,
        }

    @api.multi
    def import_mapping(self):
        self.ensure_one()
        mapping = self.env['account.bank.statement.import.sheet.mapping']\
            .create(self._get_mapping_values())
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported Mapping'),
            'res_model': 'account.bank.statement.import.sheet.mapping',
            'res_id': mapping.id,
            'view_mode': 'form',
            'view_id': False,
            'target': 'current',
        }
