.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
   :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
   :alt: License: AGPL-3

==========================
Import QIF bank statements
==========================

This module allows you to import the machine readable QIF Files in Odoo: they
are parsed and stored in human readable format in
Accounting \ Bank and Cash \ Bank Statements.

Important Note
--------------
Because of the QIF format limitation, we cannot ensure the same transactions
aren't imported several times or handle multicurrency. Whenever possible, you
should use a more appropriate file format like OFX.

The module was initiated as a backport of the new framework developed
by Odoo for V9 at its early stage. As Odoo has relicensed this module as
private inside its Odoo enterprise layer, now this one is maintained from the
original AGPL code.

Usage
=====

To use this module, you need to:

#. Go to the *Account Journal* configuration.
#. Select the right date format for qif file import.
#. Go to *Accounting* dashboard.
#. Click on *Import statement* from any of the bank journals.
#. Select a QIF file.
#. Press *Import*.

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: https://runbot.odoo-community.org/runbot/174/9.0

Bug Tracker
===========

Bugs are tracked on
`GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and
welcomed feedback.

Credits
=======

Contributors
------------    

* Odoo SA 
* Alexis de Lattre <alexis@via.ecp.fr>
* Laurent Mignon <laurent.mignon@acsone.eu>
* Ronald Portier <rportier@therp.nl>
* Pedro M. Baeza <pedro.baeza@tecnativa.com>

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
