{
    "name": "Import CSV Bank Statement from Caisse d'Epargne",
    "category": "Banking addons",
    "version": "18.0.1.0.0",
    "author": "Aurélien DUMAINE, Druidoo, Odoo Community Association (OCA)",
    "website": "https://github.com/OCA/bank-statement-import",
    "license": "AGPL-3",
    "depends": [
        "account_statement_import_file",
    ],
    "data": [
        "wizard/view_account_statement_import.xml",
    ],
    "auto_install": False,
    "installable": True,
}
