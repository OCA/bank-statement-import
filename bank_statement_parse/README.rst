The module account_bank_statement_import, backported from odoo 9.0, is
extended, to provide the functionality that was present in the 7.0 banking
addons.

Not all of the functionality described below has been implemented yet!
These were in the 7.0 version of account_banking and will be migrated
over time...

This module extends the base functionality by:

* more extensive logging
* storing much more information on each bank transaction in the bank
  statement line
* making all imports visible for the user, complete with log and data about
  user and date of import.

* Additional features for the import/export mechanism:

  * Automatic matching and creation of bank accounts, banks and partners,
    during import of statements.
  * Sound import mechanism, allowing multiple imports of the same
    transactions repeated over multiple files.

This module should make it easy to migrate bank statement import
modules written for earlies versions of Odoo/OpenERP.

Of course new parsers can also be written using the @advanced_parser
decorator provided by this module.

RECOMMENDATION

Install the web_sheet_full_width to have a good view on bank statement files.
