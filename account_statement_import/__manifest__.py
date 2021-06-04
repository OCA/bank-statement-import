# Copyright 2004-2020 Odoo S.A.
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Import Statement Files",
    "category": "Accounting",
    "version": "14.0.1.2.1",
    "license": "LGPL-3",
    "depends": ["account"],
    "author": "Odoo SA, Akretion, Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "website": "https://github.com/OCA/bank-statement-import",
    "data": [
        "security/ir.model.access.csv",
        "wizard/account_statement_import_view.xml",
        "views/account_journal.xml",
        "views/account_bank_statement_line.xml",
    ],
    "demo": [
        "demo/partner_bank.xml",
    ],
    "installable": True,
}
