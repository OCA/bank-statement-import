# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models, api


class AccountBankStatementImportTxtMap(models.Model):
    _name = 'account.bank.statement.import.map'
    _description = 'Account Bank Statement Import Txt Map'

    name = fields.Char(
        required=True,
    )
    map_line_ids = fields.One2many(
        comodel_name='account.bank.statement.import.map.line',
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
    file_encoding = fields.Selection(
        string='Encoding',
        selection=[
            ('utf-8', 'UTF-8'),
            ('utf-16 ', 'UTF-16'),
            ('windows-1252', 'Windows-1252'),
            ('latin1', 'latin1'),
            ('latin2', 'latin2'),
            ('big5', 'big5'),
            ('gb18030', 'gb18030'),
            ('shift_jis', 'shift_jis'),
            ('windows-1251', 'windows-1251'),
            ('koir8_r', 'koir9_r'),
        ],
        default='utf-8',
    )
    delimiter = fields.Selection(
        string='Separated by',
        selection=[
            ('.', 'dot (.)'),
            (',', 'comma (,)'),
            (';', 'semicolon (;)'),
            ('', 'none'),
            ('\t', 'Tab'),
            (' ', 'Space'),
        ],
        default=',',
    )
    quotechar = fields.Char(string='String delimiter', size=1,
                            default='"')

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


class AccountBankStatementImportTxtMapLine(models.Model):
    _name = 'account.bank.statement.import.map.line'
    _description = 'Account Bank Statement Import Txt Map Line'
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
        comodel_name='account.bank.statement.import.map',
        required=True,
        ondelete='cascade',
    )
    field_to_assign = fields.Selection(
        selection=[
            ('date', 'Date'),
            ('name', 'Label'),
            ('currency', 'Currency'),
            ('amount', 'Amount in the journal currency'),
            ('amount_currency', 'Amount in foreign currency'),
            ('ref', 'Reference'),
            ('note', 'Notes'),
            ('partner_name', 'Name'),
            ('account_number', 'Bank Account Number'),
        ],
        string="Statement Field to Assign",
    )
    date_format = fields.Selection(
        selection=[
            ('%d/%m/%Y', 'i.e. 15/12/2019'),
            ('%m/%d/%Y', 'i.e. 12/15/2019'),
        ],
        string="Date Format",
    )
