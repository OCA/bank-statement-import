
{
    'name': 'Import CSV Bank Statement from Caisse d\'Epargne',
    'category': 'Banking addons',
    'version': '12.0.1.0.0',
    'author': 'Aurélien DUMAINE, Druidoo',
    'website': 'https://www.druidoo.io',
    'license': 'AGPL-3',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'views/view_account_bank_statement_import.xml',
    ],
    'auto_install': False,
    'installable': True,
}
