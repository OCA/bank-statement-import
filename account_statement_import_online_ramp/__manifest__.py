# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: Ramp",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Ledo Enterprises, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account_statement_import_online"],
    "data": [
        "views/online_bank_statement_provider_views.xml",
    ],
}
