{
    "name": "Import OFX Bank Statement",
    "category": "Banking addons",
    "version": "18.0.1.0.0",
    "license": "AGPL-3",
    "author": "Odoo SA,"
    "Akretion,"
    "La Louve,"
    "GRAP,"
    "Nicolas JEUDY,"
    "Le Filament,"
    "Odoo Community Association (OCA)",
    "maintainers": ["alexis-via"],
    "development_status": "Mature",
    "website": "https://github.com/OCA/bank-statement-import",
    "depends": ["account_statement_import_file"],
    "data": ["wizard/account_statement_import.xml"],
    "external_dependencies": {"python": ["ofxparse"]},
    "installable": True,
}
