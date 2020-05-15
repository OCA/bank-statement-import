# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
    'name': 'Save imported bank statements',
    'version': '8.0.1.0.1',
    'author': 'Odoo Community Association (OCA), Therp BV',
    'license': 'AGPL-3',
    'category': 'Banking addons',
    'summary': 'Keep imported bank statements as raw data',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/account_bank_statement.xml',
    ],
    'post_init_hook': '_post_init_hook',
    'auto_install': False,
    'installable': True,
    'application': False,
}
