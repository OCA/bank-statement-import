# -*- coding: utf-8 -*-
##############################################################################
#
#    This module copyright (C) 2015 Therp BV (<http://therp.nl>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp import models


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    def copy_data(self, cr, uid, id, default=None, context=None):
        if default is None:
            default = {}
        if context is None:
            context = {}
        if 'acc_number' not in default and 'default_acc_number' not in context:
            default['acc_number'] = ''
        return super(ResPartnerBank, self).copy_data(
            cr, uid, id, default=default, context=context)

    _sql_constraints = [
        ('unique_number', 'unique(sanitized_acc_number)',
         'Account Number must be unique'),
    ]
