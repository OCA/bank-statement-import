# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: Nordigen",
    "version": "15.0.1.0.0",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "base",
        "base_iban",
        "account_statement_import_online",
        "web",
        "web_notify",
    ],
    "data": ["view/online_bank_statement_provider.xml"],
    "assets": {
        "web.assets_backend": [
            "account_bank_statement_import_online_nordigen/static/src/"
            "lib/nordigen-ui/selector.css",
            "account_bank_statement_import_online_nordigen/static/src/"
            "lib/nordigen-ui/selector.js",
            "account_bank_statement_import_online_nordigen/static/src/"
            "js/select_bank_widget.js",
        ],
        "web.assets_qweb": [
            "account_bank_statement_import_online_nordigen/static/src/xml"
            "/select_bank_widget.xml"
        ],
    },
    "external_dependencies": {
        "python": [],
    },
}
