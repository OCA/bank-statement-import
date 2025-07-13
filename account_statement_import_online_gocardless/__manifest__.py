# Copyright 2022 ForgeFlow S.L.
# Copyright 2023-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: GoCardless",
    "version": "17.0.1.0.4",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, Tecnativa, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_statement_import_online",
    ],
    "data": [
        "security/ir.model.access.csv",
        "view/online_bank_statement_provider.xml",
        "wizards/online_bank_statement_provider_existing_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_statement_import_online_gocardless/static/src/"
            "lib/gocardless-ui/selector.css",
            "account_statement_import_online_gocardless/static/src/"
            "js/select_bank_widget.esm.js",
            "account_statement_import_online_gocardless/static/src/"
            "xml/select_bank_widget.xml",
        ],
    },
}
