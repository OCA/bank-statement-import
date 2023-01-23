# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # In 14.0 this field will be provided by the
    # account_statement_import_base module.
    raw_data = fields.Text(readonly=True, copy=False)
