# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Bank Statement TXT/CSV/XLSX Import Check Number",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Ecosoft, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_statement_import_txt_xlsx",
        "bank_statement_check_number",
    ],
    "external_dependencies": {"python": ["xlrd"]},
    "data": [
        "data/map_data.xml",
        "views/account_statement_import_sheet_mapping.xml",
        "wizards/account_statement_import_sheet_mapping_wizard.xml",
    ],
    "maintainers": ["ps-tubtim"],
}
