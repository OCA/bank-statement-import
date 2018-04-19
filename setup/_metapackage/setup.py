import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo9-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo9-addon-account_bank_statement_import_camt',
        'odoo9-addon-account_bank_statement_import_camt_details',
        'odoo9-addon-account_bank_statement_import_move_line',
        'odoo9-addon-account_bank_statement_import_qif',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
