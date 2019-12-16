# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    'name': 'Bypass check Bank statement import',
    'version': '12.0.1.0.0',
    'category': 'Accounting',
    'summary': 'Allow possibility to bypass check in Bank statement import',
    'author': 'Camptocamp, '
              'Odoo Community Association (OCA)',
    'maintainer': 'Camptocamp',
    'website': 'https://github.com/OCA/bank-statement-import',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'wizard/account_bank_statement_import_view.xml',
    ],
    'license': 'AGPL-3',
    'installable': True,
    'auto_install': False,
}
