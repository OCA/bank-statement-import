# -*- coding: utf-8 -*-
{
    'name': 'Account Bank Statement Import',
    'category': 'Banking addons',
    'version': '8.0.1.1.0',
    'license': 'AGPL-3',
    'author': 'OpenERP SA,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/bank-statement-import',
    'depends': ['account'],
    'data': [
        'views/account_config_settings.xml',
        'views/account_bank_statement_import_view.xml',
        'views/account_journal.xml',
    ],
    'demo': [
        'demo/fiscalyear_period.xml',
        'demo/partner_bank.xml',
    ],
    'auto_install': False,
    'installable': True,
}
