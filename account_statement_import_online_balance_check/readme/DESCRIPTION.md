This module checks the statement lines imported by an online bank
statement provider against the data of the provider, and shows where
they stop matching.

It works with any provider: it asks the provider for the transactions of
the period again, without importing them, and compares them with the
statement lines by their import ID.
