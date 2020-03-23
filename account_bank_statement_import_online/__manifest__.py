# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'Online Bank Statements',
    'version': '12.0.1.0.1',
    'author':
        'Brainbean Apps, '
        'Dataplug, '
        'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/bank-statement-import/',
    'license': 'AGPL-3',
    'category': 'Accounting',
    'summary': 'Online bank statements update',
    'depends': [
        'account',
        'account_bank_statement_import',
        'web_widget_dropdown_dynamic',
    ],
    'data': [
        'data/account_bank_statement_import_online.xml',
        'security/ir.model.access.csv',
        'security/online_bank_statement_provider.xml',
        'views/account_journal.xml',
        'views/online_bank_statement_provider.xml',
        'wizards/online_bank_statement_pull_wizard.xml',
    ],
    'installable': True,
}
