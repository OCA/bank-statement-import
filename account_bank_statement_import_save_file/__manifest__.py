# Copyright 2015-2019 Therp BV (<http://therp.nl>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

{
    'name': 'Save imported bank statements',
    'version': '13.0.1.0.0',
    'author': 'Odoo Community Association (OCA), Therp BV',
    'license': 'AGPL-3',
    'category': 'Banking addons',
    'summary': 'Attach imported bank statement file to the bank statement',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/account_bank_statement.xml',
    ],
    'installable': True,
    'application': False,
}
