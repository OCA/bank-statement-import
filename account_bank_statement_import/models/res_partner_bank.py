# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of account_bank_statement_import,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     account_bank_statement_importis free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     account_bank_statement_import is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with account_bank_statement_import_coda.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

import re
from openerp import api, models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    sanitized_acc_number = fields.Char(
        'Sanitized Account Number', size=64, readonly=True,
        compute='_get_sanitized_account_number', store=True, index=True)
    enforce_unique_import_lines = fields.Boolean(
        string='Force unique lines on import',
        help="Some banks do not provide an unique id for transactions in"
             " bank statements. In some cases it is possible that multiple"
             " downloads contain overlapping transactions. In that case"
             " activate this option to generate a unique id based on all the"
             " information in the transaction. This prevents duplicate"
             " imports, at the cost of - in exceptional cases - missing"
             " transactions when all the information in two or more"
             " transactions is the same.\n"
             "This setting is only relevant for banks linked to a company."
    )

    def _sanitize_account_number(self, acc_number):
        if acc_number:
            return re.sub(r'\W+', '', acc_number).upper()
        return False

    @api.one
    @api.depends('acc_number')
    def _get_sanitized_account_number(self):
        self.sanitized_acc_number = self._sanitize_account_number(
            self.acc_number)

    @api.model
    def search(self, args, offset=0, limit=None, order=None, count=False):
        pos = 0
        while pos < len(args):
            if args[pos][0] == 'acc_number':
                op = args[pos][1]
                value = args[pos][2]
                if hasattr(value, '__iter__'):
                    value = [self._sanitize_account_number(i) for i in value]
                else:
                    value = self._sanitize_account_number(value)
                if 'like' in op:
                    value = '%' + value + '%'
                args[pos] = ('sanitized_acc_number', op, value)
            pos += 1
        return super(ResPartnerBank, self).search(
            args, offset=offset, limit=limit, order=order, count=count)
