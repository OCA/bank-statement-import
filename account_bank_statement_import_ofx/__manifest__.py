{
    'name': 'Import OFX Bank Statement',
    'category': 'Banking addons',
    'version': '12.0.1.1.0',
    'license': 'AGPL-3',
    'author': 'Odoo SA,'
              'Akretion,'
              'La Louve,'
              'GRAP,'
              'Nicolas JEUDY,'
              'Le Filament,'
              'Odoo Community Association (OCA)',
    'website': 'https://odoo-community.org/',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/view_account_bank_statement_import.xml',
    ],
    'external_dependencies': {
        'python': ['ofxparse'],
    },
    'installable': True,
}
