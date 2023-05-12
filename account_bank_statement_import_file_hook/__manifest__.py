# Copyright 2023 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
{
    "name": "Account Bank Statement Import File Hook",
    "version": "13.0.1.0.0",
    # see https://odoo-community.org/page/development-status
    "development_status": "Production/Stable",
    "category": "Invoicing Management",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "ForgeFlow, Odoo Community Association (OCA)",
    "license": "LGPL-3",
    "depends": ["account_bank_statement_import"],
    "post_load": "post_load_hook",
}
