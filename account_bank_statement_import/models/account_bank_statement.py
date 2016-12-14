# -*- coding: utf-8 -*-
# Copyright 2009-2016 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import api, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'

    @api.model
    def create(self, vals):
        if vals.get('name'):
            journal = self.env['account.journal'].browse(
                vals.get('journal_id'))
            if journal.enforce_sequence:
                vals['name'] = '/'
        return super(AccountBankStatement, self).create(vals)
