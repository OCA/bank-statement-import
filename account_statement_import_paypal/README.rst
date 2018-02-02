Import Paypal Bank Statements
=============================

This module allows you to import the Paypal CSV files in Odoo as bank statements.

Configuration
=============

In the menu Accounting > Configuration > Accounts > Setup your Bank Accounts, make sure that you have your Paypal bank account with the following parameters:
* Bank Account Type: Normal Bank Account
* Account Number: the email address associated with your Paypal account
* Account Journal: the journal associated to your Paypal account

============

Go to Paypal and download your Bank Statement

.. image:: account_bank_statement_import_paypal/static/description/paypal_backoffice.png
    :alt: .
.. image:: static/description/paypal_backoffice.png
    :alt: .

Credits
=======

Contributors
------------

* Alexis de Lattre <alexis.delattre@akretion.com>
* Sebastien BEAU <sebastien.beau@akretion.com>

TIPS
--------
For now only French and English report are supported
For adding new support you just need to add your header in model/account_bank_statement_import_paypal.py in the variables HEADERS.
Please help us and do a PR for adding new header ! Thanks

Maintainer
----------

.. image:: http://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: http://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose mission is to support the collaborative development of Odoo features and promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
