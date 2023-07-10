==================================
Online Bank Statements: OFX
==================================

This module provides online bank statements from Open Financial Exchange (OFX) institutions.
You can set-up your own provider, or import a list of supported providers.
https://ofxhome.com/ is used as a data source, currently over 300 institutions are supported.


**Table of contents**

.. contents::
   :local:

Configuration
=============

To configure online bank statements provider:

#. Go to *Invoicing > Configuration > Journals*
#. Open bank journal to configure and edit it
#. Set *Bank Feeds* to *Online*
#. Select *OFX* as online bank statements provider in
   *Online Bank Statements (OCA)* section
#. Save the bank journal
#. Click on provider and configure provider-specific settings.

Usage
=====

To pull historical bank statements:

#. Go to *Invoicing > Configuration > Journals*
#. Select specific bank accounts
#. Launch *Actions > Online Bank Statements Pull Wizard*
#. Configure date interval and click *Pull*

Known issues / Roadmap
======================


Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed
`feedback <https://github.com/OCA/bank-statement-import/issues/new?body=module:%20account_statement_import_online_paypal%0Aversion:%2014.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Do not contact contributors directly about support or help with technical issues.

Credits
=======

Authors
~~~~~~~

* ForgeFlow

Contributors
~~~~~~~~~~~~

* `ForgeFlow <https://www.forgeflow.com/>`__

  * Jasmin Solanki <jasmin.solanki@forgeflow.com>
