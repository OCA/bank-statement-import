# -*- coding: utf-8 -*-
# Copyright 2017 Open Net Sàrl
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    camt_ref_type = fields.Char(string='Type of reference', max=35)
