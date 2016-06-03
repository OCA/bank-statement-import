# -*- coding: utf-8 -*-
{
    'name': 'Import OFX Bank Statement',
    'category': 'Banking addons',
    'version': '9.0.0.0.0',
    'author': 'OpenERP SA,'
              'La Louve,'
              'Odoo Community Association (OCA)',
    'website': 'https://odoo-community.org/',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/view_account_bank_statement_import.xml',
    ],
    'demo': [
        'demo/demo_data.xml',
    ],
    'external_dependencies': {
        'python': ['ofxparse'],
    },
    'auto_install': False,
    'installable': True,
}
