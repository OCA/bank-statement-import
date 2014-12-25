# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
#              (C) 2011-2104 Therp BV (<http://therp.nl>).
#              (C) 2011 Smile (<http://smile.fr>).
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
#    along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Bank Statement Import Parse',
    'version': '0.5',
    'license': 'AGPL-3',
    'author': 'Banking addons community',
    'website': 'https://github.com/OCA/banking',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import',
        ],
    'data': [
        'security/ir.model.access.csv',
        'view/menu.xml',
    ],
    'js': [
    ],
    'description': '''
    Base module to write parsers for bank statement import files.

    The module account_bank_statement_import, backported from odoo 9.0, is
    extended, so parsers developed might hope to be compatible with future
    development of Odoo.
    ''',
    'installable': True,
    'auto_install': False,
}
