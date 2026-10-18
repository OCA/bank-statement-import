# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
{
    "name": "Online Bank Statements: finAPI",
    "version": "16.0.1.0.0",
    "category": "Accounting",
    "summary": "Online bank statements via finAPI Access (PSD2, Germany / EU)",
    "license": "AGPL-3",
    "author": "Agent ERP GmbH, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "development_status": "Beta",
    "maintainers": ["agent-z28"],
    "depends": [
        "account_statement_import_online",
    ],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_config_parameter.xml",
        "data/mail_template.xml",
        "data/ir_cron.xml",
        "views/online_bank_statement_provider.xml",
        "views/finapi_webform_templates.xml",
        "wizards/finapi_webform_wizard.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "account_statement_import_online_finapi/static/src/js/"
            "finapi_error_dialogs.esm.js",
        ],
    },
    "installable": True,
    "application": False,
}
