# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
{
    "name": "Account Bank Online",
    "version": "13.0.1.0.0",
    "category": "Account",
    "website": "https://github.com/OCA/bank-statement-import",
    "author": "Florent de Labarre, Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "installable": True,
    "depends": ["account"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_cron.xml",
        "view/account_journal.xml",
        "view/account_bank_provider.xml"],
}
