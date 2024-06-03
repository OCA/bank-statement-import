
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/bank-statement-import&target_branch=16.0)
[![Pre-commit Status](https://github.com/OCA/bank-statement-import/actions/workflows/pre-commit.yml/badge.svg?branch=16.0)](https://github.com/OCA/bank-statement-import/actions/workflows/pre-commit.yml?query=branch%3A16.0)
[![Build Status](https://github.com/OCA/bank-statement-import/actions/workflows/test.yml/badge.svg?branch=16.0)](https://github.com/OCA/bank-statement-import/actions/workflows/test.yml?query=branch%3A16.0)
[![codecov](https://codecov.io/gh/OCA/bank-statement-import/branch/16.0/graph/badge.svg)](https://codecov.io/gh/OCA/bank-statement-import)
[![Translation Status](https://translation.odoo-community.org/widgets/bank-statement-import-16-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/bank-statement-import-16-0/?utm_source=widget)

<!-- /!\ do not modify above this line -->

# OCA bank statement import modules for Odoo

This repository hosts additionnal parsers and import features for bank statements.

<!-- /!\ do not modify below this line -->

<!-- prettier-ignore-start -->

[//]: # (addons)

Available addons
----------------
addon | version | maintainers | summary
--- | --- | --- | ---
[account_statement_import_base](account_statement_import_base/) | 16.0.1.0.0 | [![alexis-via](https://github.com/alexis-via.png?size=30px)](https://github.com/alexis-via) | Base module for Bank Statement Import
[account_statement_import_camt](account_statement_import_camt/) | 16.0.1.0.2 |  | CAMT Format Bank Statements Import
[account_statement_import_camt54](account_statement_import_camt54/) | 16.0.1.0.0 |  | Bank Account Camt54 Import
[account_statement_import_file](account_statement_import_file/) | 16.0.1.0.2 | [![alexis-via](https://github.com/alexis-via.png?size=30px)](https://github.com/alexis-via) | Import Statement Files
[account_statement_import_file_reconcile_oca](account_statement_import_file_reconcile_oca/) | 16.0.1.0.0 | [![alexis-via](https://github.com/alexis-via.png?size=30px)](https://github.com/alexis-via) | Import Statement Files and Go Direct to Reconciliation
[account_statement_import_ofx](account_statement_import_ofx/) | 16.0.1.0.0 | [![alexis-via](https://github.com/alexis-via.png?size=30px)](https://github.com/alexis-via) | Import OFX Bank Statement
[account_statement_import_online](account_statement_import_online/) | 16.0.1.2.2 | [![alexey-pelykh](https://github.com/alexey-pelykh.png?size=30px)](https://github.com/alexey-pelykh) | Online bank statements update
[account_statement_import_online_gocardless](account_statement_import_online_gocardless/) | 16.0.1.1.0 |  | Online Bank Statements: GoCardless
[account_statement_import_online_ofx](account_statement_import_online_ofx/) | 16.0.1.0.0 |  | Online bank statements for OFX
[account_statement_import_online_paypal](account_statement_import_online_paypal/) | 16.0.1.0.1 | [![alexey-pelykh](https://github.com/alexey-pelykh.png?size=30px)](https://github.com/alexey-pelykh) | Online bank statements for PayPal.com
[account_statement_import_online_ponto](account_statement_import_online_ponto/) | 16.0.1.1.1 |  | Online Bank Statements: MyPonto.com
[account_statement_import_online_qonto](account_statement_import_online_qonto/) | 16.0.1.0.0 |  | Online Bank Statements: Qonto
[account_statement_import_qif](account_statement_import_qif/) | 16.0.1.0.0 |  | Import QIF Bank Statements
[account_statement_import_sheet_file](account_statement_import_sheet_file/) | 16.0.1.1.2 | [![alexey-pelykh](https://github.com/alexey-pelykh.png?size=30px)](https://github.com/alexey-pelykh) | Import TXT/CSV or XLSX files as Bank Statements in Odoo

[//]: # (end addons)

<!-- prettier-ignore-end -->

## Licenses

This repository is licensed under [AGPL-3.0](LICENSE).

However, each module can have a totally different license, as long as they adhere to Odoo Community Association (OCA)
policy. Consult each module's `__manifest__.py` file, which contains a `license` key
that explains its license.

----
OCA, or the [Odoo Community Association](http://odoo-community.org/), is a nonprofit
organization whose mission is to support the collaborative development of Odoo features
and promote its widespread use.
