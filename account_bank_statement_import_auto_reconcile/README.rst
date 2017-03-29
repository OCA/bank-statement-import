.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :target: http://www.gnu.org/licenses/agpl-3.0-standalone.html
    :alt: License: AGPL-3

=====================================
Automatic reconciliation after import
=====================================

This addon allows you have Odoo reconcile transactions from a bank statement import automatically in cases where the matching transaction can be determined unambigously.

Configuration
=============

To configure this module, you need to:

#. go to the journal your bank account uses
#. in the field ``Automatic reconciliation rules``, add at least one rule

Usage
=====

After a journal is configured for automatic reconciliations, it simply happens during an import on this journal. If there were automatic reconciliations, you'll see a notification about that and the lines in question will also show up as reconciled.

Reconciliation rules
--------------------

    Odoo standard
        Do exactly what Odoo does when proposing reconciliations. This searches for an exact match on amount and reference first, but falls back to less exact matches if none are found before. If there's only one match, do the reconciliation
    Exact amount and reference
        Strictly only match if we have the same partner, amount and reference

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
    :alt: Try me on Runbot
    :target: https://runbot.odoo-community.org/runbot/174/8.0

Background
==========

Mainly, this module is a framework for conveniently (for programmers) adding new custom automatic reconciliation rules. To do this, study the provided AbstractModels.

Known issues / Roadmap
======================

* add more matching rules:
    * AmountDiffuse (let the user configure the threshold)
    * SameCompany (if A from company C bought it, but B from the same company/organization pays)
    * AmountTransposedDigits (reconcile if only two digits are swapped. Dangerous and a special case of AmountDiffuse)
    * whatever else we can think of
* add some helpers/examples for using the options field
* allow to fiddle with the parameters of configured rules during a specific import

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/OCA/bank-statement-import/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* Odoo Community Association: `Icon <https://github.com/OCA/maintainer-tools/blob/master/template/module/static/description/icon.svg>`_.

Contributors
------------

* Holger Brunn <hbrunn@therp.nl>

Do not contact contributors directly about help with questions or problems concerning this addon, but use the `community mailing list <mailto:community@mail.odoo.com>`_ or the `appropriate specialized mailinglist <https://odoo-community.org/groups>`_ for help, and the bug tracker linked in `Bug Tracker`_ above for technical issues.

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
