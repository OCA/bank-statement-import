By default, in Odoo 16 and later, deleting an `account.bank.statement` will only remove the grouping, leaving the actual bank statement lines behind in the system (as they manifest as independent journal entries).

This module alters that behavior so that when you delete an `account.bank.statement`, it cascades the deletion to its included `account.bank.statement.line` records, effectively cleaning up both the statement and all of its associated lines off the database.

This is especially helpful for canceling and deleting incorrectly imported bank statements entirely.
