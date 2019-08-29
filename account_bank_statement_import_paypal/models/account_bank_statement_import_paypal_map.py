# Copyright 2019 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class AccountBankStatementImportPaypalMap(models.Model):
    _name = 'account.bank.statement.import.paypal.map'

    name = fields.Char(
        required=True,
    )
    map_line_ids = fields.One2many(
        comodel_name='account.bank.statement.import.paypal.map.line',
        inverse_name='map_parent_id',
        string="Map lines",
        required=True,
        copy=True,
    )
    float_thousands_sep = fields.Selection(
        [('dot', 'dot (.)'),
         ('comma', 'comma (,)'),
         ('none', 'none'),
         ],
        string='Thousands separator',
        # forward compatibility: this was the value assumed
        # before the field was added.
        default='dot',
        required=True
    )
    float_decimal_sep = fields.Selection(
        [('dot', 'dot (.)'),
         ('comma', 'comma (,)'),
         ('none', 'none'),
         ],
        string='Decimals separator',
        # forward compatibility: this was the value assumed
        # before the field was added.
        default='comma',
        required=True
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

    def _get_separators(self):
        separators = {'dot': '.',
                      'comma': ',',
                      'none': '',
                      }
        return (separators[self.float_thousands_sep],
                separators[self.float_decimal_sep])


class AccountBankStatementImportPaypalMapLIne(models.Model):
    _name = 'account.bank.statement.import.paypal.map.line'
    _order = "sequence asc, id asc"

    sequence = fields.Integer(
        string="Field number",
        required=True,
    )
    name = fields.Char(
        string="Header Name",
        required=True,
    )
    map_parent_id = fields.Many2one(
        comodel_name='account.bank.statement.import.paypal.map',
        required=True,
        ondelete='cascade',
    )
    field_to_assign = fields.Selection(
        selection=[
            ('date', 'Date'),
            ('time', 'Time'),
            ('description', 'Description'),
            ('currency', 'Currency'),
            ('amount', 'Gross'),
            ('commission', 'Fee'),
            ('balance', 'Balance'),
            ('transaction_id', 'Transaction ID'),
            ('email', 'From Email Address'),
            ('partner_name', 'Name'),
            ('bank_name', 'Bank Name'),
            ('bank_account', 'Bank Account'),
            ('invoice_number', 'Invoice ID'),
            ('origin_transaction_id', 'Origin Transaction ID'),
        ],
        string="Statement Field to Assign",
    )
    date_format = fields.Selection(
        selection=[
            ('%d/%m/%Y', 'i.e. 15/12/2019'),
            ('%m/%d/%Y', 'i.e. 12/15/2019'),
            ('%d.%m.%Y', 'i.e. 15.12.2019')
        ],
        string="Date Format",
    )
