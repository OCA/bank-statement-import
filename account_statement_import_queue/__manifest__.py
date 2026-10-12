# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

{
    "name": "Account Statement Import Queue",
    "version": "18.0.1.0.0",
    "category": "Accounting",
    "summary": "Import bank statements using queue jobs with history tracking.",
    "author": "Heliconia Solutions Pvt. Ltd., Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "depends": [
        "account_statement_import_sheet_file",
        "queue_job",
    ],
    "data": [
        "security/import_bank_statement_history_security.xml",
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "views/import_bank_statement_history_views.xml",
        "wizard/account_statement_import_view.xml",
    ],
    "installable": True,
    "application": True,
    "development_status": "Beta",
    "maintainers": ["Bhavesh Heliconia"],
    "auto_install": False,
    "license": "AGPL-3",
}
