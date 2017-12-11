.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================
Bank Statement MT940
====================

This module provides a generic parser for MT940 files. Given that MT940 is a
non-open non-standard of pure evil in the way that every bank cooks up its own
interpretation of it, this addon alone won't help you much. It is rather
intended to be used by other addons to implement the dialect specific to a
certain bank.

See account_bank_statement_import_mt940_nl_ing for an example on how to use it.

Known issues / Roadmap
======================

* None

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/bank-statement-import/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smash it by providing detailed and welcomed feedback.

Credits
=======

Contributors
------------

* Stefan Rijnhart <srijnhart@therp.nl>
* Ronald Portier <rportier@therp.nl>
* Andrea Stirpe <a.stirpe@onestein.nl>
* Fekete Mihai <mihai.fekete@forbiom.eu>

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
