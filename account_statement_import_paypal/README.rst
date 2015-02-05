Import Paypal Bank Statements
=============================

This module allows you to import the Paypal CSV files in Odoo as bank statements.

Installation
============

This module depends on the module *account_bank_statement_import* which
is available:
* for Odoo version 8: in the OCA project `bank-statement-import <https://github.com/OCA/bank-statement-import>`
* for Odoo master (future version 9): it is an official module.

Configuration
=============

In the menu Accounting > Configuration > Accounts > Setup your Bank Accounts, make sure that you have your Paypal bank account with the following parameters:
* Bank Account Type: Normal Bank Account
* Account Number: the email address associated with your Paypal account
* Account Journal: the journal associated to your Paypal account

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
