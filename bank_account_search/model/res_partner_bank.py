# -*- coding: utf-8 -*-
"""Extend res.partner.bank."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    All other contributions are (C) by their respective contributors
#
#    All Rights Reserved
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
import re
import logging
from openerp import fields, models
from openerp.tools.translate import _


_logger = logging.getLogger(__name__)


class ResPartnerBank(models.Model):
    """Extend res.partner.bank."""
    _inherit = 'res.partner.bank'

    def init(self, cr):
        """Make sure all existing records have search_account_number filled."""
        cr.execute(
            "SELECT id, acc_number FROM res_partner_bank"
            " WHERE search_account_number IS NULL"
            " OR search_account_number = ''"
        )
        records = cr.fetchall()
        if records:
            _logger.info(_('Setting search_account_number in bank accounts.'))
        for record in records:
            account_id = record[0]
            acc_number = record[1]
            search_account_number = self.normalize(acc_number)
            cr.execute(
                "UPDATE res_partner_bank"
                " SET search_account_number = %s"
                " WHERE id = %s",
                (search_account_number, account_id)
            )

    def normalize(self, acc_number):
        """Do away with whitespace in bank account number."""
        search_account_number = acc_number.upper()
        search_account_number = re.sub(r'\s', '', search_account_number)
        search_account_number = re.sub(r'-._()', '', search_account_number)
        return search_account_number

    def compute_values(self, cr, uid, data, context=None):
        """Ensure each bank-account has number reliable for searching.

        Bank account numbers may be formatted in various ways. Removing
        whitespace and other formatting, and ensuring string is in uppercase
        will give a searchable field.
        """
        if 'search_account_number' not in data and 'acc_number' in data:
            # Do not override explicitly set search_account_number:
            data['search_account_number'] = self.normalize(data['acc_number'])
        return data

    def create(self, cr, uid, data, context=None):
        """Override create to fill desired fields."""
        data = self.compute_values(cr, uid, data, context=context)
        result = super(ResPartnerBank, self).create(
            cr, uid, data, context=context)
        return result

    def write(self, cr, uid, ids, data, context=None):
        """Override write to fill desired fields."""
        data = self.compute_values(cr, uid, data, context=context)
        result = super(ResPartnerBank, self).write(
            cr, uid, ids, data, context=context)
        return result

    def search(
            self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        """Override search to use search_account_number instead of
        acc_number"""
        search_args = []
        for arg in args:
            if arg[0] in ['acc_number', 'search_account_number']:
                arg = (
                    'search_account_number',
                    arg[1],
                    self.normalize(arg[2]),
                )
            search_args.append(arg)
        return super(ResPartnerBank, self).search(
            cr, uid, search_args, offset=offset, limit=limit, order=order,
            context=context, count=count
        )

    def name_search(
            self, cr, uid, name, args, operator='ilike',
            limit=100, context=None):
        """Override name_search to first on search_account_number"""
        search_account_number = self.normalize(name)
        search_args = [('search_account_number', '=', search_account_number)]
        res = super(ResPartnerBank, self).name_search(
            cr, uid, '', search_args, operator=operator, limit=limit,
            context=context
        )
        # Return result, or try again with default
        return res or super(ResPartnerBank, self).name_search(
            cr, uid, name, args, operator=operator, limit=limit,
            context=context
        )

    search_account_number = fields.Char(
        string='Search account number', size=64,
        help="""Normalized version of account number""",
    )

    _sql_constraints = [
        ('unique_number', 'unique(search_account_number)',
         'Account Number must be unique'),
    ]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
