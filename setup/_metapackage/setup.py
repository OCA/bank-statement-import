import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo8-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo8-addon-account_bank_statement_import',
        'odoo8-addon-account_bank_statement_import_camt',
        'odoo8-addon-account_bank_statement_import_mt940_base',
        'odoo8-addon-account_bank_statement_import_mt940_nl_ing',
        'odoo8-addon-account_bank_statement_import_mt940_nl_rabo',
        'odoo8-addon-account_bank_statement_import_ofx',
        'odoo8-addon-account_bank_statement_import_qif',
        'odoo8-addon-account_bank_statement_import_save_file',
        'odoo8-addon-base_bank_account_number_unique',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
    ]
)
