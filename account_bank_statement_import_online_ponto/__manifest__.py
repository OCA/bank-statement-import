# Copyright 2020 Florent de Labarre.
# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Online Bank Statements: MyPonto.com",
    "version": "12.0.1.3.0",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author":
        "Florent de Labarre"
        ", Therp BV"
        ", Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account_bank_statement_import_online"],
    "data": [
        "data/ir_cron.xml",
        "security/ir.model.access.csv",
        "views/online_bank_statement_provider.xml",
        "views/ponto_buffer.xml",
        "views/ir_actions_act_window.xml",
        "views/ir_ui_menu.xml",
    ],
}
