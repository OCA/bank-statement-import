# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2013-2015 Therp BV <http://therp.nl>
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
    'name': 'CAMT Format Bank Statements Import',
    'version': '8.0.0.4.1',
    'summary': 'Module to import SEPA CAMT.053 Format bank statement files',
    'license': 'AGPL-3',
    'author': 'Odoo Community Association (OCA), Therp BV',
    'website': 'https://github.com/OCA/bank-statement-import',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'installable': True,
}
