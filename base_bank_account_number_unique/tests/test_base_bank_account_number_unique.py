# -*- coding: utf-8 -*-
##############################################################################
#
#    This module copyright (C) 2015 Therp BV <http://therp.nl>.
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
from openerp.tests.common import TransactionCase
from openerp import exceptions
from ..hooks import post_init_hook


class TestBaseBankAccountNumberUnique(TransactionCase):
    def test_base_bank_account_number_unique(self):
        # drop our constraint, insert nonunique account numbers and see if
        # the init hook catches this
        self.env['ir.model.constraint'].search([
            ('name', '=', 'res_partner_bank_unique_number'),
            ('model.model', '=', 'res.partner.bank'),
        ])._module_data_uninstall()
        self.env['res.partner.bank'].create({
            'acc_number': 'BE1234567890',
            'state': 'bank',
        })
        self.env['res.partner.bank'].create({
            'acc_number': 'BE 1234 567 890',
            'state': 'bank',
        })
        with self.assertRaises(exceptions.Warning):
            post_init_hook(self.cr, self.registry)
