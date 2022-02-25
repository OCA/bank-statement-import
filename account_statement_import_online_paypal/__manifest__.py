# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020-2021 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Online Bank Statements: PayPal.com",
    "version": "14.0.1.0.0",
    "author": "CorporateHub, Odoo Community Association (OCA)",
    "maintainers": ["alexey-pelykh"],
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "category": "Accounting",
    "summary": "Online bank statements for PayPal.com",
    "depends": ["account_statement_import_online"],
    "data": ["views/online_bank_statement_provider.xml"],
    "installable": True,
}
