This module is the successor of the module **account_bank_statement_import** that was part of Odoo Community until Odoo v13 and was moved to Odoo Enterprise for Odoo v14 (cf `this commit <https://github.com/odoo/odoo/commit/9ba8734f15e1a292ca27b1a026e8366a91b2a8c9>`_). We decided to change its name and the name of the wizard object it provides in order to avoid a conflict with the Enterprise module.

This module has several additionnal feature:

* support multi-account bank statement files,
* attach the file to the bank statement (to facilitate the diagnostic in case of problem),
* improved error messages.

This module only provides the technical framework for the import of statement files. You must also install the format-specific modules to add support for the statement file formats that your banks/provide use. For example, the OCA module **account_statement_import_ofx** will add support for the OFX (Open Financial Exchange) file format. You will find those modules in the OCA project `bank-statement-import <https://github.com/OCA/bank-statement-import>`_ or, for the country-specific formats, in the OCA localization projects.
