.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Bank Statement Parse Camt
=========================

Module to import SEPA CAMT.053 Format bank statement files.

Based on the Banking addons framework.

Configuration
=============

The user can configure the way CAMT bank statements are imported:

* Go to *Accounting* -> *Configuration* -> *Journals* -> *Journals*
* Find the Journal that is related to the bank account you are importing for
* Set the *Aggregate batch transactions (CAMT)* checkbox

If the checkbox is false, the import will load every single line of the TxDtls details;
instead if it's true, it will load only the total amount of each batch of lines.

To be able to access the configuration settings, the user must enable Technical features.

Known issues / Roadmap
======================

* None

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/bank-statement-import/issues/new?body=module:%20account_bank_statement_import%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------

* Stefan Rijnhart <srijnhart@therp.nl>
* Ronald Portier <rportier@therp.nl>
* Andrea Stirpe <a.stirpe@onestein.nl>
* Tom Blauwendraat <tom@sunflowerweb.nl>
* Dan Kiplangat <dan@sunflowerweb.nl>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit http://odoo-community.org.
This module should make it easy to migrate bank statement import
modules written for earlies versions of Odoo/OpenERP.
