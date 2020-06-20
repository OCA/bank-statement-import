# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Bank Statement Import TXT XLSX",
    "summary": "Import TXT/CSV or XLSX files as Bank Statements in Odoo",
    "version": "13.0.1.0.2",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, Brainbean Apps, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_bank_statement_import",
        "multi_step_wizard",
        "web_widget_dropdown_dynamic",
    ],
    "external_dependencies": {"python": ["csv", "xlrd"]},
    "data": [
        "security/ir.model.access.csv",
        "data/map_data.xml",
        "views/account_bank_statement_import_sheet_mapping.xml",
        "views/account_bank_statement_import.xml",
        "views/account_journal_views.xml",
        "wizards/account_bank_statement_import_sheet_mapping_wizard.xml",
    ],
}
