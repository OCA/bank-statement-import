## 19.0.1.0.0

- Migration to 19.0.
- Import only the account chosen for the journal. A Plaid login can
  hold several accounts, which were all imported into the same journal.
- Leave out pending transactions, which get a new ID once posted and
  were imported twice.
- Keep the bank's transaction dates in the provider's timezone.
- Fetch the whole pull range from Plaid once, instead of once per
  statement period.
- Scheduled pulls look back 14 days (*Plaid Lookback*), so transactions
  that post a few days after their date are not missed.
- Share one Plaid login between providers (*Use Plaid Login Of*).
- *Reconnect Bank* opens Link in update mode for expired logins.
  *Unlink from Plaid* removes the login at Plaid.
- The access token is readable by administrators only.
- Load Plaid Link from Plaid's CDN, as Plaid requires, instead of a
  bundled copy.
