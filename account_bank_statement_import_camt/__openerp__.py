# -*- coding: utf-8 -*-
# © 2013-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'CAMT Format Bank Statements Import',
    'version': '9.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Odoo Community Association (OCA), Therp BV',
    'website': 'https://github.com/OCA/bank-statement-import',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/account_bank_statement_import.xml',
    ],
}
