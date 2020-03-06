# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Account Bank Statement Import Multi',
    'summary': """
        Allow to import multiple statement on multiple journals
        using account_bank_statement_import""",
    'version': '11.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'ACSONE SA/NV,Odoo Community Association (OCA)',
    'website': 'https://acsone.eu/',
    'depends': [
        'account',
        'account_bank_statement_import',
    ],
    'data': [
        'wizards/account_bank_statement_import_multi.xml',
    ],
}
