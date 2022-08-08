
[![Runboat](https://img.shields.io/badge/runboat-Try%20me-875A7B.png)](https://runboat.odoo-community.org/builds?repo=OCA/bank-statement-import&target_branch=15.0)
[![Pre-commit Status](https://github.com/OCA/bank-statement-import/actions/workflows/pre-commit.yml/badge.svg?branch=15.0)](https://github.com/OCA/bank-statement-import/actions/workflows/pre-commit.yml?query=branch%3A15.0)
[![Build Status](https://github.com/OCA/bank-statement-import/actions/workflows/test.yml/badge.svg?branch=15.0)](https://github.com/OCA/bank-statement-import/actions/workflows/test.yml?query=branch%3A15.0)
[![codecov](https://codecov.io/gh/OCA/bank-statement-import/branch/15.0/graph/badge.svg)](https://codecov.io/gh/OCA/bank-statement-import)
[![Translation Status](https://translation.odoo-community.org/widgets/bank-statement-import-15-0/-/svg-badge.svg)](https://translation.odoo-community.org/engage/bank-statement-import-15-0/?utm_source=widget)

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
[account_bank_statement_clear_partner](account_bank_statement_clear_partner/) | 15.0.1.0.1 |  | Clear all partners in bank statement lines
[account_statement_import](account_statement_import/) | 15.0.2.1.0 | [![alexis-via](https://github.com/alexis-via.png?size=30px)](https://github.com/alexis-via) | Import Statement Files
[account_statement_import_camt](account_statement_import_camt/) | 15.0.1.0.0 |  | CAMT Format Bank Statements Import
[account_statement_import_camt54](account_statement_import_camt54/) | 15.0.1.0.0 |  | Bank Account Camt54 Import
[account_statement_import_online](account_statement_import_online/) | 15.0.1.0.0 | [![alexey-pelykh](https://github.com/alexey-pelykh.png?size=30px)](https://github.com/alexey-pelykh) | Online bank statements update
[account_statement_import_online_ponto](account_statement_import_online_ponto/) | 15.0.1.0.0 |  | Online Bank Statements: MyPonto.com

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
