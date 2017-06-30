.. image:: https://img.shields.io/badge/licence-AGPL--3-blue.svg
    :alt: License: AGPL-3

Unique bank account numbers
===========================

It can be desirable to be able to rely on a bank account number identifying
exactly one partner. This module allows you to enforce this, so that an
account number is unique in the system.

There are some valid corner cases were it is valid to have multiple records
for the same account number. For instance in a multicompany setup where the
bank-account linked to one company, is a partner bank account for another
company.

Because of these corner cases, the constraint is no longer implemented as
a SQL unique index. This has the added advantage, that the module can be
installed on databases where the bank-account numbers are not unique already.

To find records that are not unique, you could use the following SQL
statement.

    with res_partner_bank_sanitized as (
        select
            id, acc_number, coalesce(company_id, 0) as company_id,
            sanitized_acc_number
        from res_partner_bank
    ),
    res_partner_bank_sanitized_grouped as (
        select
            array_agg(id) ids, sanitized_acc_number, count(*) kount,
            company_id
        from res_partner_bank_sanitized
        group by sanitized_acc_number, company_id
    )
    select * from res_partner_bank_sanitized_grouped where kount > 1;

Installation
============

The constraint is active for new and changed numbers, from the moment of
installation.


Bug Tracker
===========

Bugs are tracked on
`GitHub Issues <https://github.com/OCA/bank-statement-import/issues>`_.

Credits
=======

Contributors
------------

* Holger Brunn <hbrunn@therp.nl>
* Ronald Portier <ronald@therp.nl>

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
