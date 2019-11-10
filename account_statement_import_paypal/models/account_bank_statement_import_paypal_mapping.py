# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountBankStatementImportPayPalMapping(models.Model):
    _name = 'account.bank.statement.import.paypal.mapping'
    _description = 'Account Bank Statement Import PayPal Mapping'

    name = fields.Char(
        required=True,
    )
    float_thousands_sep = fields.Selection(
        string='Thousands Separator',
        selection=[
            ('dot', 'dot (.)'),
            ('comma', 'comma (,)'),
            ('none', 'none'),
        ],
        default='dot',
        required=True,
    )
    float_decimal_sep = fields.Selection(
        string='Decimals Separator',
        selection=[
            ('dot', 'dot (.)'),
            ('comma', 'comma (,)'),
            ('none', 'none'),
        ],
        default='comma',
        required=True,
    )
    date_format = fields.Char(
        string='Date Format',
        required=True,
    )
    time_format = fields.Char(
        string='Time Format',
        required=True,
    )
    date_column = fields.Char(
        string='"Date" column',
        required=True,
    )
    time_column = fields.Char(
        string='"Time" column',
        required=True,
    )
    tz_column = fields.Char(
        string='"Timezone" column',
        required=True,
    )
    name_column = fields.Char(
        string='"Name" column',
        required=True,
    )
    currency_column = fields.Char(
        string='"Currency" column',
        required=True,
    )
    gross_column = fields.Char(
        string='"Gross" column',
        required=True,
    )
    fee_column = fields.Char(
        string='"Fee" column',
        required=True,
    )
    balance_column = fields.Char(
        string='"Balance" column',
        required=True,
    )
    transaction_id_column = fields.Char(
        string='"Transaction ID" column',
        required=True,
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

    @api.onchange('float_thousands_sep')
    def onchange_thousands_separator(self):
        if 'dot' == self.float_thousands_sep == self.float_decimal_sep:
            self.float_decimal_sep = 'comma'
        elif 'comma' == self.float_thousands_sep == self.float_decimal_sep:
            self.float_decimal_sep = 'dot'

    @api.onchange('float_decimal_sep')
    def onchange_decimal_separator(self):
        if 'dot' == self.float_thousands_sep == self.float_decimal_sep:
            self.float_thousands_sep = 'comma'
        elif 'comma' == self.float_thousands_sep == self.float_decimal_sep:
            self.float_thousands_sep = 'dot'

    @api.multi
    def _get_float_separators(self):
        self.ensure_one()
        separators = {
            'dot': '.',
            'comma': ',',
            'none': '',
        }
        return (separators[self.float_thousands_sep],
                separators[self.float_decimal_sep])
