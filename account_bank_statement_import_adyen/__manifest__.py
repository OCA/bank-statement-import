# © 2017 Opener BV (<https://opener.amsterdam>)
# © 2020 Vanmoof BV (<https://www.vanmoof.com>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
{
    "name": "Adyen statement import",
    "version": "12.0.1.0.0",
    "author": "Opener BV, Vanmoof BV, Odoo Community Association (OCA)",
    "category": "Banking addons",
    "website": "https://github.com/oca/bank-statement-import",
    "license": "AGPL-3",
    "depends": [
        "account_bank_statement_import",
        "account_bank_statement_clearing_account",
    ],
    "external_dependencies": {
        "python": [
            "openpyxl",
        ],
    },
    "data": [
        "views/account_journal.xml",
    ],
    "installable": True,
}
