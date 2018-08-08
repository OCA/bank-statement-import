# Copyright 2017 Tecnativa - Luis M. Ontalba
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

{
    'name': 'Bank statement import move lines',
    'version': '11.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Import journal items into bank statement',
    'author': 'Tecnativa, '
              'Odoo Community Association (OCA)',
    'website': 'https://www.tecnativa.com',
    'depends': [
        'account',
    ],
    'data': [
        'wizards/account_statement_line_create_view.xml',
        'views/account_bank_statement_view.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
}
