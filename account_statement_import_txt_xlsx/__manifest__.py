# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bank Statement TXT/CSV/XLSX Import",
    "summary": "Import TXT/CSV or XLSX files as Bank Statements in Odoo",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, CorporateHub, Odoo Community Association (OCA)",
    "maintainers": ["alexey-pelykh"],
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_statement_import_file",
    ],
    "external_dependencies": {"python": ["xlrd", "chardet"]},
    "data": [
        "security/ir.model.access.csv",
        "data/map_data.xml",
        "views/account_statement_import_sheet_mapping.xml",
        "views/account_statement_import.xml",
        "views/account_journal_views.xml",
    ],
}
