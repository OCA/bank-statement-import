# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Online Bank Statements Import Split',
    'version': '12.0.1.0.0',
    'author':
        'Brainbean Apps, '
        'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/bank-statement-import/',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'summary': 'Split statements during import',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/account_bank_statement_import.xml',
    ],
    'installable': True,
}
