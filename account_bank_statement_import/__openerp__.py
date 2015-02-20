# -*- encoding: utf-8 -*-
# noqa: This is a backport from Odoo. OCA has no control over style here.
# flake8: noqa
{
    'name': 'Account Bank Statement Import',
    'category' : 'Accounting & Finance',
    'version': '1.0',
    'author': 'OpenERP SA',
    'depends': ['account'],
    'demo': [],
    'description' : """Generic Wizard to Import Bank Statements.
    
    Backport from Odoo 9.0
    """,
    'data' : [
        'account_bank_statement_import_view.xml',
    ],
    'demo': [
        'demo/fiscalyear_period.xml',
        'demo/partner_bank.xml',
    ],
    'auto_install': False,
    'installable': True,
}
