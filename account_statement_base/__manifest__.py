# Copyright 2023 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Bank Statement Base",
    "version": "17.0.1.0.0",
    "category": "Accounting",
    "license": "LGPL-3",
    "summary": "Base module for Bank Statements",
    "author": "Akretion,Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "development_status": "Mature",
    "website": "https://github.com/OCA/account-reconcile",
    "depends": ["account"],
    "data": [
        "views/account_bank_statement.xml",
        "views/account_bank_statement_line.xml",
    ],
    "installable": True,
}
