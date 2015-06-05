.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Import OFX Bank Statement
=========================

This module allows you to import the machine readable OFX Files in Odoo: they are parsed and stored in human readable format in 
Accounting \ Bank and Cash \ Bank Statements.

Bank Statements may be generated containing a subset of the OFX information (only those transaction lines that are required for the 
creation of the Financial Accounting records). 

The module has been initiated by a backport of the new framework developed
by Odoo for V9 at its early stage. It's no more kept in sync with the V9 since
it has reach a stage where maintaining a pure backport of 9.0 in 8.0 is not
feasible anymore 

Installation
============

The module requires one additional python lib:

* `ofxparse <http://pypi.python.org/pypi/ofxparse>`_

Known issues / Roadmap
======================

* None

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/bank-statement-import/issues/new?body=module:%20account_bank_statement_import_ofx%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.


Credits
=======

Contributors
------------    

* Odoo SA 
* Alexis de Lattre <alexis@via.ecp.fr>
* Laurent Mignon <laurent.mignon@acsone.eu>
* Ronald Portier <rportier@therp.nl>

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
