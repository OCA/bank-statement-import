# -*- coding: utf-8 -*-
# © 2017 Compassion CH <http://www.compassion.ch>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    'name': 'CAMT Debitor Details Bank Statements Import',
    'version': '10.0.1.0.0',
    'license': 'AGPL-3',
    'author': 'Odoo Community Association (OCA), Compassion CH',
    'website': 'https://github.com/OCA/bank-statement-import',
    'category': 'Banking addons',
    'depends': [
        'account_bank_statement_import_camt',
    ],
    'data': [
        'views/account_bank_statement_line.xml',
    ],
    'qweb': [
        'static/src/xml/camt_details_reconciliation_layout.xml',
    ]
}
