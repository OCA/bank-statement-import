import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo10-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo10-addon-account_bank_statement_import_camt',
        'odoo10-addon-account_bank_statement_import_camt_details',
        'odoo10-addon-account_bank_statement_import_camt_oca',
        'odoo10-addon-account_bank_statement_import_move_line',
        'odoo10-addon-account_bank_statement_import_mt940_base',
        'odoo10-addon-account_bank_statement_import_ofx',
        'odoo10-addon-account_bank_statement_import_qif',
        'odoo10-addon-account_bank_statement_import_save_file',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
