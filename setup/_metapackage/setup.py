import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo12-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo12-addon-account_bank_statement_import_camt_oca',
        'odoo12-addon-account_bank_statement_import_ofx',
        'odoo12-addon-account_bank_statement_import_paypal',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
