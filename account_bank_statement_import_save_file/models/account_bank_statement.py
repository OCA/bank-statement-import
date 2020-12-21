# Copyright 2015-2019 Therp BV (<http://therp.nl>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    import_file = fields.Many2one(
        'ir.attachment', 'Import file', readonly=True)
    import_date = fields.Datetime(
        related='import_file.create_date', string='Imported on')
    import_user = fields.Many2one(
        related='import_file.create_uid', string='Imported by')
    import_log = fields.Text(
        related='import_file.description', string='Import Warnings')
