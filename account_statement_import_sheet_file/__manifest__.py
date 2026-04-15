# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bank Statement TXT/CSV/XLSX Import",
    "summary": "Import TXT/CSV or XLSX files as Bank Statements in Odoo",
    "version": "19.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, CorporateHub, Odoo Community Association (OCA)",
    "maintainers": ["alexey-pelykh"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_statement_import_file",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/account_statement_import_sheet_mapping.xml",
        "views/account_statement_import.xml",
        "views/account_journal_views.xml",
    ],
    "demo": [
        "demo/map_data_demo.xml",
    ],
}
