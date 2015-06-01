# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of account_bank_statement_import_coda,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     account_bank_statement_import_coda is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     account_bank_statement_import_coda is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with account_bank_statement_import_coda.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name': 'Account Bank Statement Batch Import',
    'author': "ACSONE SA/NV,Odoo Community Association (OCA)",
    'website': "http://www.acsone.eu",
    'category': 'Accounting & Finance',
    'version': '1.0',
    'license': 'AGPL-3',
    'depends': [
        'account_bank_statement_import'
    ],
    'data': [
        'wizard/account_bank_statement_import_result.xml',
    ],
    'auto_install': False,
    'installable': True,
}
