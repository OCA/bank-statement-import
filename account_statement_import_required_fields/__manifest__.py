# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Statement Import Required Fields",
    "summary": "Enforce mandatory columns during bank statement import (TXT/CSV/XLSX)",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "author": "Heliconia Solutions Pvt. Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "depends": [
        "account",
        "account_statement_import_sheet_file",
    ],
    "data": [
        "views/account_statement_import_sheet_mapping_view.xml",
    ],
    "maintainers": ["Bhavesh Heliconia"],
    "installable": True,
    "application": False,
    "auto_install": False,
}
