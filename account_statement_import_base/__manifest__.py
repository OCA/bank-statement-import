# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Base module for Bank Statement Import",
    "category": "Accounting",
    "version": "18.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["account_statement_base"],
    "author": "Akretion, Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "development_status": "Mature",
    "website": "https://github.com/OCA/bank-statement-import",
    "data": [
        "views/account_bank_statement_line.xml",
    ],
    "installable": True,
}
