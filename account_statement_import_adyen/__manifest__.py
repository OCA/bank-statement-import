# Copyright 2017 Opener BV <https://opener.amsterdam>
# Copyright 2020 Vanmoof BV <https://www.vanmoof.com>
# Copyright 2021 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Adyen statement import",
    "version": "13.0.1.0.0",
    "author": "Opener BV, Vanmoof BV, Odoo Community Association (OCA)",
    "category": "Banking addons",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "depends": [
        "base_import",
        "account_bank_statement_import",
        "account_bank_statement_clearing_account",
    ],
    "data": ["views/account_journal.xml"],
    "installable": True,
}
