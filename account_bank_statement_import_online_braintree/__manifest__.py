# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: BraintreePayments.com",
    "summary": "Online bank statements for BraintreePayments.com",
    "version": "12.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import/",
    "author": "CorporateHub, Odoo Community Association (OCA)",
    "maintainers": ["alexey-pelykh"],
    "license": "AGPL-3",
    "application": False,
    "installable": True,
    "depends": [
        "account_bank_statement_import_online",
        "web_widget_dropdown_dynamic",
    ],
    "external_dependencies": {
        "python": [
            "braintree",
        ]
    },
    "data": [
        "views/online_bank_statement_provider.xml",
    ]
}
