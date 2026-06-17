# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bank Statement XLS Import",
    "summary": "Import XLS files as Bank Statements in Odoo",
    "version": "19.0.2.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "external_dependencies": {"python": ["xlrd"]},
    "depends": [
        "account_statement_import_sheet_file",
    ],
}
