# Copyright 2019 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


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
        ],
        string="Date Format",
    )
