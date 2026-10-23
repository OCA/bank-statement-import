# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements FinTS",
    "summary": "Pull bank statements from German banks via FinTS/HBCI",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "MT Software, Odoo Community Association (OCA)",
    "maintainers": ["mt-software-de"],
    "license": "AGPL-3",
    "external_dependencies": {"python": ["fints>=4.2.4"]},
    "depends": [
        "account_statement_import_online",
        "account_statement_import_camt",
        "account_statement_import_generate_unique_id",
    ],
    "data": [
        "security/ir.model.access.csv",
        "wizards/online_bank_statement_fints_tan.xml",
        "views/account_journal.xml",
        "views/online_bank_statement_provider.xml",
    ],
}
