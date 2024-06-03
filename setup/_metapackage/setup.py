import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo-addon-account_statement_import_base>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_camt54>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_camt>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_file>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_file_reconcile_oca>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_ofx>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_online>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_online_gocardless>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_online_ofx>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_online_paypal>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_online_ponto>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_online_qonto>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_qif>=16.0dev,<16.1dev',
        'odoo-addon-account_statement_import_sheet_file>=16.0dev,<16.1dev',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 16.0',
    ]
)
