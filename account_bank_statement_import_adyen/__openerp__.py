# coding: utf-8
# © 2017 Opener BV (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'Adyen statement import',
    'version': '8.0.1.0.0',
    'author': 'Opener BV, Odoo Community Association (OCA)',
    'category': 'Banking addons',
    'website': 'https://github.com/oca/bank-statement-import',
    'depends': [
        'account_bank_statement_import',
        'account_bank_statement_clearing_account',
    ],
    'data': [
        'views/account_journal.xml',
    ],
    'installable': True,
}
