# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Statement Line Clearing Date",
    "version": "18.0.1.0.0",
    "category": "Accounting/Accounting",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "summary": "Order bank statements by a line's clearing date.",
    "depends": [
        "account_statement_base",
    ],
    "data": [
        "views/account_bank_statement_line_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
