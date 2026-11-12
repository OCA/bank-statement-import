# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Online Bank Statements: Soldo",
    "version": "18.0.1.0.0",
    "author": "Luca Orioli, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Online bank statements for Soldo prepaid cards",
    "depends": ["account_statement_import_online"],
    "data": ["views/online_bank_statement_provider.xml"],
    "installable": True,
}
