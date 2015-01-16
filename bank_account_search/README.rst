Make searching for bank accounts more intelligent
=================================================

Bank accounts can be formatted in various ways and users and banks will not
always be consistent in how the specify account numbers.  This causes two
problems:

* Testing for the uniqueness of account-numbers. When creating a new
  bank account, it may have the same account number as an existing one,
  only stored in a different format;
* Seaching for account numbers, for instance when importing bank statements,
  because the formatting of the search string may differ from the formatting
  in the database.

The module bank_account_search solves these problems by having an extra field
search_account_number, that will always store the account number without any
formatting. It will also override the search function of model
res.partner.bank to actually search on the new field instead of the old one,
and by doing away with all formatting in the search string.

There will also be an sql unique constraint on the search_account_number field
to prevent duplication of accounts.

The module will not only override write and create to ensure the
search_account_number field is always filled in the right way, but will also
on module update or installation update all existing records that don't have
the field set.
