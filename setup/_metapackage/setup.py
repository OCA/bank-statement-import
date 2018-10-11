import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo11-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo11-addon-account_bank_statement_import_camt_oca',
        'odoo11-addon-account_bank_statement_import_move_line',
        'odoo11-addon-account_bank_statement_import_mt940_base',
        'odoo11-addon-account_bank_statement_import_ofx',
        'odoo11-addon-account_bank_statement_import_qif',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
