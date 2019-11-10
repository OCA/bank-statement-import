# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models, _
from odoo.exceptions import UserError

from base64 import b64decode
from os import path


class AccountBankStatementImportPayPalMappingWizard(models.TransientModel):
    _name = 'account.bank.statement.import.paypal.mapping.wizard'
    _description = 'Account Bank Statement Import PayPal Mapping Wizard'

    data_file = fields.Binary(
        string='Bank Statement File',
        required=True,
    )
    filename = fields.Char()

    @api.multi
    def import_mapping(self):
        self.ensure_one()
        mapping_values = {
            'name': _('Mapping from %s') % path.basename(self.filename),
            'float_thousands_sep': 'comma',
            'float_decimal_sep': 'dot',
            'date_format': '%d/%m/%Y',
            'time_format': '%H:%M:%S',
        }
        header = self.env['account.bank.statement.import.paypal.parser'] \
            .parse_header(b64decode(self.data_file))
        if len(header) == 22:
            mapping_values.update({
                'date_column': header[0],
                'time_column': header[1],
                'tz_column': header[2],
                'name_column': header[3],
                'currency_column': header[6],
                'gross_column': header[7],
                'fee_column': header[8],
                'balance_column': header[18],
                'transaction_id_column': header[12],
                'type_column': header[4],
                'from_email_address_column': header[10],
                'to_email_address_column': header[11],
                'invoice_id_column': header[16],
                'subject_column': header[20],
                'note_column': header[21],
            })
        elif len(header) == 18:
            mapping_values.update({
                'date_column': header[0],
                'time_column': header[1],
                'tz_column': header[2],
                'name_column': header[11],
                'currency_column': header[4],
                'gross_column': header[5],
                'fee_column': header[6],
                'balance_column': header[8],
                'transaction_id_column': header[9],
                'description_column': header[3],
                'from_email_address_column': header[10],
                'invoice_id_column': header[16],
                'bank_name_column': header[12],
                'bank_account_column': header[13],
            })
        else:
            raise UserError(_(
                'File structure does not look like a PayPal report, please '
                'check the file or create the mapping manually.'
            ))
        mapping = self.env['account.bank.statement.import.paypal.mapping']\
            .create(mapping_values)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Imported Mapping'),
            'res_model': 'account.bank.statement.import.paypal.mapping',
            'res_id': mapping.id,
            'view_mode': 'form',
            'view_id': False,
            'target': 'new',
        }
