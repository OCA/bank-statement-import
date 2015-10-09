# -*- encoding: utf-8 -*-
{
    'name': 'Import OFX Bank Statement',
    'category': 'Banking addons',
    'version': '8.0.1.0.0',
    'author': 'OpenERP SA,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/bank-statement-import',
    'depends': [
        'account_bank_statement_import'
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
