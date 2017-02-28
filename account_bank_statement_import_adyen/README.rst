.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

======================
Adyen statement import
======================

This module processes Adyen transaction statements in xlsx format. You can
import the statements in a dedicated journal. Reconcile your sale invoices
with the credit transations. Reconcile the aggregated counterpart
transaction with the transaction in your real bank journal and register the
aggregated fee line containing commision and markup on the applicable
cost account.

Configuration
=============

Configure a pseudo bank journal by creating a new journal with a dedicated
Adyen clearing account as the default ledger account. Set your merchant
account string in the Advanced settings on the journal form.

Usage
=====

After installing this module, you can import your Adyen transaction statements
through Menu Finance -> Bank -> Import. Don't enter a journal in the import
wizard.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/174/8.0


Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/bank-statement-import/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Stefan Rijnhart <stefan@opener.am>

Maintainer
----------

.. image:: https://odoo-community.org/logo.png
   :alt: Odoo Community Association
   :target: https://odoo-community.org

This module is maintained by the OCA.

OCA, or the Odoo Community Association, is a nonprofit organization whose
mission is to support the collaborative development of Odoo features and
promote its widespread use.

To contribute to this module, please visit https://odoo-community.org.
