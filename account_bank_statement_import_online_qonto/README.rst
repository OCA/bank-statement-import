=============================
Online Bank Statements: Qonto
=============================

.. |badge1| image:: https://img.shields.io/badge/maturity-Beta-yellow.png
    :target: https://odoo-community.org/page/development-status
    :alt: Beta
.. |badge2| image:: https://img.shields.io/badge/licence-AGPL--3-blue.png
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3
.. |badge3| image:: https://img.shields.io/badge/github-OCA%2Fbank--statement--import-lightgray.png?logo=github
    :target: https://github.com/OCA/bank-statement-import/tree/12.0/account_bank_statement_import_online_qonto
    :alt: OCA/bank-statement-import
.. |badge4| image:: https://img.shields.io/badge/weblate-Translate%20me-F47D42.png
    :target: https://translation.odoo-community.org/projects/bank-statement-import-12-0/bank-statement-import-12-0-account_bank_statement_import_online_qonto
    :alt: Translate me on Weblate
.. |badge5| image:: https://img.shields.io/badge/runbot-Try%20me-875A7B.png
    :target: https://runbot.odoo-community.org/runbot/174/12.0
    :alt: Try me on Runbot

|badge1| |badge2| |badge3| |badge4| |badge5|

This module provides online bank statements from Qonto Bank.

**Table of contents**

.. contents::
   :local:

Configuration
=============

To configure online bank statements provider:

#. Go to *Invoicing > Configuration > Bank Accounts*
#. Open bank account to configure and edit it
#. Set *Bank Feeds* to *Online*
#. Select *Qonto.eu* as online bank statements provider in
   *Online Bank Statements (OCA)* section
#. Save the bank account
#. Click on provider and configure provider-specific settings.

or, alternatively:

#. Go to *Invoicing > Overview*
#. Open settings of the corresponding journal account
#. Switch to *Bank Account* tab
#. Set *Bank Feeds* to *Online*
#. Select *Qonto.eu* as online bank statements provider in
   *Online Bank Statements (OCA)* section
#. Save the bank account
#. Click on provider and configure provider-specific settings.

To obtain *Login* and *Key*:

#. Open `Qonto.eu <https://app.qonto.eu/>`_.
#. Go to *Settings*
#. Go to *Api Integration*, click *Generate Key*

Usage
=====

To pull historical bank statements:

#. Go to *Invoicing > Configuration > Bank Accounts*
#. Select specific bank accounts
#. Launch *Actions > Online Bank Statements Pull Wizard*
#. Configure date interval and click *Pull*

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
`feedback <https://github.com/OCA/bank-statement-import/issues/new?body=module:%20account_bank_statement_import_online_qonto%0Aversion:%2012.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* Florent de Labarre

Maintainers
~~~~~~~~~~~

This module is maintained by the OCA.

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

This module is part of the `OCA/bank-statement-import <https://github.com/OCA/bank-statement-import/tree/12.0/account_bank_statement_import_online_qonto>`_ project on GitHub.

You are welcome to contribute. To learn how please visit https://odoo-community.org/page/Contribute.
