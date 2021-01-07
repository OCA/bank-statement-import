# Copyright 2004-2020 Odoo S.A.
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

{
    "name": "Account Bank Statement Import",
    "category": "Accounting/Accounting",
    "version": "13.0.1.0.0",
    "license": "LGPL-3",
    "depends": ["account"],
    "description": """Generic Wizard to Import Bank Statements.

(This module does not include any type of import format.)

OFX and QIF imports are available in Enterprise version.""",
    "author": "Odoo SA",
    "data": [
        "account_bank_statement_import_view.xml",
        "account_import_tip_data.xml",
        "wizard/journal_creation.xml",
        "views/account_bank_statement_import_templates.xml",
    ],
    "demo": [
        "demo/partner_bank.xml",
    ],
    "installable": True,
    "auto_install": True,
}
