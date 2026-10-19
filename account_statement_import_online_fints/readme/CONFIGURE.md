FinTS requires a product registration number, which Die Deutsche
Kreditwirtschaft assigns for free at
<https://www.fints.org/de/hersteller/produktregistrierung>.

To configure the provider:

1.  Go to *Invoicing \> Configuration \> Journals* and open the bank
    journal, its bank account must be set.
2.  Set *Bank Feeds* to *Online* and select *FinTS* as provider.
3.  As administrator, open the provider and fill in the bank code
    (BLZ), the FinTS server URL of your bank, your login, your PIN and
    the FinTS product ID.
4.  Click on *Connect*. Confirm the access with a TAN or in your
    banking app, as asked by the wizard.

The PIN and the state of the FinTS connection, including the account
numbers and names provided by the bank, are stored unencrypted in the
database. Restrict the access to the database and its backups
accordingly. Only administrators can read and set them; this applies to
the password of the providers of other services too.

The transactions provided via FinTS carry no unique identifier.
Selecting FinTS as provider therefore enables *Generate Missing Import
IDs* of `account_statement_import_generate_unique_id` on the journal. It
cannot be disabled while FinTS is the provider of the journal, otherwise
pulling an overlapping period would duplicate the lines.

The available TAN methods are listed after the first connection. To use
another one than the automatically selected method, set its code as *TAN
Method* and connect again.

Check also the configuration of `account_statement_import_online` for
the schedule of the pulls.

Some banks ask to confirm every access in their banking app. For them,
set *Wait for App Confirmation* to the minutes a pull waits for the
confirmation, and schedule the pulls when you can confirm them, e.g.
once a day.

While waiting, the pull keeps an Odoo worker busy. With multiple workers,
Odoo stops a scheduled pull after `limit_time_real_cron` seconds (by
default `limit_time_real`, 120 seconds) and a manual pull after
`limit_time_real` seconds. Keep the waiting time below these limits or
raise them accordingly.
