# Copyright 2004-2020 Odoo S.A.
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Import Statement Files",
    "category": "Accounting",
    "version": "16.0.1.0.2",
    "license": "LGPL-3",
    "depends": ["account_statement_import_base"],
    "author": "Odoo SA, Akretion, Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "development_status": "Mature",
    "website": "https://github.com/OCA/bank-statement-import",
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_statement_import_view.xml",
        "views/account_journal.xml",
    ],
    "demo": [
        "demo/partner_bank.xml",
    ],
    "installable": True,
}
