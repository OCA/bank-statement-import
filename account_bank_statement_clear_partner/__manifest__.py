# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Clear all partners in bank statement lines",
    "version": "12.0.1.0.0",
    # see https://odoo-community.org/page/development-status
    "development_status": "Production/Stable",
    "category": "Invoicing Management",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "depends": [
        'account',
    ],
    "data": [
        "views/account_bank_statement_views.xml"
    ]
}
