This module allows you to import the machine readable QIF Files in Odoo: they
are parsed and stored in human readable format in
Accounting \ Bank and Cash \ Bank Statements.

Important Note
~~~~~~~~~~~~~~
Because of the QIF format limitation, we cannot ensure the same transactions
aren't imported several times or handle multicurrency. Whenever possible, you
should use a more appropriate file format like OFX.

The module was initiated as a backport of the new framework developed
by Odoo for V9 at its early stage. As Odoo has relicensed this module as
private inside its Odoo enterprise layer, now this one is maintained from the
original AGPL code.
