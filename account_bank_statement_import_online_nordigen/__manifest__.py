# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: Nordigen",
    "version": "12.0.1.0.0",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["base", "base_iban", "account_bank_statement_import_online", "web"],
    "data": ["view/assets.xml", "view/online_bank_statement_provider.xml"],
    "qweb": ["static/src/xml/*.xml"],
    "external_dependencies": {"python": []},
}
