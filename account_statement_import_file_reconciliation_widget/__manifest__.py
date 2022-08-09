# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

{
    "name": "Import Statement Files and Go Direct to Reconciliation",
    "category": "Accounting",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "depends": ["account_statement_import", "account_reconciliation_widget"],
    "author": "Akretion, Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/bank-statement-import",
    "data": [
        "wizards/account_statement_import_view.xml",
    ],
    "installable": True,
    "auto_install": True,
}
