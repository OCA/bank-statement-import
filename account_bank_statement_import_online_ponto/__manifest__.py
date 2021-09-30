# Copyright 2020 Florent de Labarre
# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: MyPonto.com",
    "version": "13.0.1.0.1",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Florent de Labarre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account_bank_statement_import_online"],
    "data": ["view/online_bank_statement_provider.xml"],
}
