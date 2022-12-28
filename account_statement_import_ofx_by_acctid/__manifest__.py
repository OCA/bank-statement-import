# Copyright 2022 - TODAY, Escodoo
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Import OFX Bank Statement by ACCTID",
    "summary": """
        Import OFX Bank Statement by ACCTID""",
    "category": "Banking addons",
    "version": "14.0.1.0.0",
    "license": "AGPL-3",
    "author": "Escodoo,Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "depends": [
        "account_statement_import_ofx",
    ],
    "data": [
        "views/res_partner_bank.xml",
    ],
    "demo": [],
}
