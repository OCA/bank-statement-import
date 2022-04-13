# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Online Bank Statements",
    "version": "15.0.1.0.0",
    "author": "CorporateHub, Odoo Community Association (OCA)",
    "maintainers": ["alexey-pelykh"],
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Online bank statements update",
    "external_dependencies": {"python": ["odoo_test_helper"]},
    "depends": [
        "account",
        "account_statement_import",
        "web_widget_dropdown_dynamic",
    ],
    "data": [
        "data/account_statement_import_online.xml",
        "security/ir.model.access.csv",
        "security/online_bank_statement_provider.xml",
        "wizards/online_bank_statement_pull_wizard.xml",
        "views/actions.xml",
        "views/account_journal.xml",
        "views/account_bank_statement_line.xml",
        "views/online_bank_statement_provider.xml",
    ],
    "installable": True,
}
