# Copyright 2026 Daniel Lo Nigro <d@d.sb>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

{
    "name": "Online Bank Statements and OCA Reconciliation",
    "summary": "Open transaction lines when online imports do not create statements",
    "category": "Accounting",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "depends": ["account_statement_import_online", "account_reconcile_oca"],
    "installable": True,
    "auto_install": True,
}
