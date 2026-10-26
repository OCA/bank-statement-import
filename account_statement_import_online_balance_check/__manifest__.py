# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Online Bank Statements: Balance Check",
    "version": "18.0.1.0.0",
    "author": "Luca Orioli, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Compare the imported statement lines with the data of the provider",
    "depends": ["account_statement_import_online"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/online_bank_statement_check.xml",
        "views/online_bank_statement_provider.xml",
    ],
    "installable": True,
}
