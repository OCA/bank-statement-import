# Copyright 2020 Florent de Labarre.
# Copyright 2020 Tecnativa - João Marques.
# Copyright 2022-2023 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: MyPonto.com",
    "version": "16.0.1.1.1",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Florent de Labarre, Therp BV, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account_statement_import_online"],
    "data": [
        "views/online_bank_statement_provider.xml",
    ],
}
