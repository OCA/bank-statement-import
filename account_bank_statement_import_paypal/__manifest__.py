# Copyright 2014-2017 Akretion (http://www.akretion.com).
# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    'name': 'PayPal CSV Format Bank Statements Import',
    'summary': 'Import PayPal CSV files as Bank Statements in Odoo',
    'version': '12.0.2.2.1',
    'category': 'Accounting',
    'website': 'https://github.com/OCA/bank-statement-import',
    'author':
        'Akretion, '
        'Brainbean Apps, '
        'Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'installable': True,
    'depends': [
        'account_bank_statement_import',
        'multi_step_wizard',
        'web_widget_dropdown_dynamic',
    ],
    'external_dependencies': {
        'python': [
            'csv',
        ]
    },
    'data': [
        'security/ir.model.access.csv',
        'data/maps.xml',
        'views/account_bank_statement_import_paypal_mapping.xml',
        'views/account_bank_statement_import.xml',
        'wizards/account_bank_statement_import_paypal_mapping_wizard.xml',
    ],
}
