# Copyright 2023 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

{
    "name": "Online Bank Statements: OFX",
    "version": "16.0.1.0.0",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Online bank statements for OFX",
    "depends": [
        "account_statement_import_online",
    ],
    "external_dependencies": {"python": ["ofxtools", "ofxparse"]},
    "data": [
        "security/ir.model.access.csv",
        "views/online_bank_statement_provider.xml",
        "wizards/online_bank_statement_pull_wizard.xml",
    ],
    "installable": True,
}
