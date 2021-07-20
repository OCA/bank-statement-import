# Copyright 2014-2017 Akretion (http://www.akretion.com).
# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "PayPal CSV Format Bank Statements Import",
    "summary": "Import PayPal CSV files as Bank Statements in Odoo",
    "version": "14.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Akretion, CorporateHub, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": [
        "account_statement_import",
        "multi_step_wizard",
        "web_widget_dropdown_dynamic",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/maps.xml",
        "views/account_statement_import_paypal_mapping.xml",
        "views/account_statement_import.xml",
        "wizards/account_statement_import_paypal_mapping_wizard.xml",
    ],
}
