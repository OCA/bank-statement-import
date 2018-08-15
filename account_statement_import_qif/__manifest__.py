# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Import QIF Bank Statements',
    'category': 'Accounting',
    'version': '11.0.1.0.1',
    'author': 'OpenERP SA,'
              'Tecnativa,'
              'Odoo Community Association (OCA)',
    'website': 'https://github.com/OCA/bank-statement-import',
    'depends': [
        'account_bank_statement_import',
    ],
    'data': [
        'wizards/account_bank_statement_import_qif_view.xml',
    ],
    'installable': True,
    'license': 'AGPL-3',
}
