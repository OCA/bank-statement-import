This module pulls the bank statements of German banks directly via
FinTS (formerly HBCI), without any third party service in between.

The transactions are fetched as MT940 statements or, for banks which do
not offer them, as CAMT reports, imported with the CAMT parser of
`account_statement_import_camt`.

Due to PSD2 the bank asks to confirm the access (strong customer
authentication) from time to time, usually every 90 or 180 days, some
banks on every access. The confirmation is done in Odoo with a TAN or,
for decoupled methods, in the banking app. In between, the statements
are pulled automatically.
