# Copyright 2022 Karolin Schlegel
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: FinTS",
    "version": "14.0.1.0.0",
    "category": "Account",
    "author": "Karolin Schlegel, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "external dependencies": {"python": ["fints"]},
    "depends": ["account_statement_import_online"],
    "data": ["view/online_bank_statement_provider.xml"],
}
