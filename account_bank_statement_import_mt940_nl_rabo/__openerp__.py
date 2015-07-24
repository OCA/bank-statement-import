# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2014-2015 Therp BV <http://therp.nl>.
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
{
    'name': 'MT940 import for dutch Rabobank',
    'version': '1.1',
    'author': 'Odoo Community Association (OCA), Therp BV',
    'website': 'https://github.com/OCA/bank-statement-import',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import_mt940_base'
    ],
    'auto_install': False,
    'installable': True,
    'application': False,
}
