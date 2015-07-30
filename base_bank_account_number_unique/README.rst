.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3
Unique bank account numbers
===========================

It can be desirable to be able to rely on a bank account number identifying exactly one partner. This module allows you to enforce this, so that an account number is unique in the system.

Installation
============

During installation, the module checks if your bank account numbers are unique already. If this is not the case, you won't be able to install the module until duplicates are fixed.

The error message only shows the first few duplicates, in order to find all of them, use the following statement::

    with res_partner_bank_sanitized as (select id, acc_number, regexp_replace(acc_number, '\W+', '', 'g') acc_number_sanitized from res_partner_bank),
         res_partner_bank_sanitized_grouped as (select array_agg(id) ids, acc_number_sanitized, count(*) amount from res_partner_bank_sanitized group by acc_number_sanitized)
         select * from res_partner_bank_sanitized_grouped where amount > 1;

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.
In case of trouble, please check there if your issue has already been reported.
If you spotted it first, help us smashing it by providing a detailed and welcomed feedback
`here <https://github.com/OCA/bank-statement-import/issues/new?body=module:%20base_bank_account_number_unique%0Aversion:%208.0%0A%0A**Steps%20to%20reproduce**%0A-%20...%0A%0A**Current%20behavior**%0A%0A**Expected%20behavior**>`_.

Credits
=======

Contributors
------------

* Holger Brunn <hbrunn@therp.nl>

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
