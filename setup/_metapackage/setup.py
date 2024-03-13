import setuptools

with open('VERSION.txt', 'r') as f:
    version = f.read().strip()

setuptools.setup(
    name="odoo14-addons-oca-bank-statement-import",
    description="Meta package for oca-bank-statement-import Odoo addons",
    version=version,
    install_requires=[
        'odoo14-addon-account_statement_import',
        'odoo14-addon-account_statement_import_base',
        'odoo14-addon-account_statement_import_camt',
        'odoo14-addon-account_statement_import_camt54',
        'odoo14-addon-account_statement_import_file_reconciliation_widget',
        'odoo14-addon-account_statement_import_move_line',
        'odoo14-addon-account_statement_import_ofx',
        'odoo14-addon-account_statement_import_ofx_by_acctid',
        'odoo14-addon-account_statement_import_online',
        'odoo14-addon-account_statement_import_online_paypal',
        'odoo14-addon-account_statement_import_online_ponto',
        'odoo14-addon-account_statement_import_online_ponto_ing',
        'odoo14-addon-account_statement_import_online_wise',
        'odoo14-addon-account_statement_import_paypal',
        'odoo14-addon-account_statement_import_sftp',
        'odoo14-addon-account_statement_import_txt_xlsx',
    ],
    classifiers=[
        'Programming Language :: Python',
        'Framework :: Odoo',
        'Framework :: Odoo :: 14.0',
    ]
)
