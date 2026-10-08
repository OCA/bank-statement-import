# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

{
    "name": "Bank Statement Import Generate Unique ID",
    "summary": "Generate a unique import ID for statement lines without one",
    "category": "Accounting",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["account_statement_import_base"],
    "author": "MT Software, Odoo Community Association (OCA)",
    "maintainers": ["mt-software-de"],
    "development_status": "Beta",
    "website": "https://github.com/OCA/bank-statement-import",
    "data": [
        "views/account_journal.xml",
    ],
    "installable": True,
}
