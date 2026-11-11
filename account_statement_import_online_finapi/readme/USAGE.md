Once configured, no further user action is needed:

- The scheduled action **Pull Online Bank Statements** (provided by `account_statement_import_online`) reads the
  transactions finAPI has stored, at the configured interval.
- You can also trigger a read manually from the bank account form: click _Online Sync_.

How the data stays fresh (`finAPI Data Refresh` on the provider):

- **Web Form background update (default):** before each scheduled read the pull triggers finAPI's
  `POST /api/tasks/backgroundUpdate`. Within a valid recurring PSD2 consent this completes **without any user
  interaction**, so finAPI fetches the latest bookings from the bank and Odoo imports them. This is the right mode for
  the standard finAPI product, where finAPI holds the PSD2 license (Web Form). `GET /transactions` alone only ever
  returns what finAPI already stored, so without this refresh the pull keeps returning the same (stale) set.
- **Direct update (licensed TPP only):** uses the customer-not-present `POST /bankConnections/update`. Choose this only
  if your mandator holds its **own** PSD2/TPP license — finAPI rejects the call for Web Form mandators.
- **No refresh:** only read what finAPI already has. Use this when finAPI's server-side **Automatic Batch Update** keeps
  the connection fresh for you.

In every refreshing mode the refresh is **best-effort and throttled** to at most once every six hours (the PSD2 limit is
four customer-not-present accesses per day). A failure (e.g. the bank requires Strong Customer Authentication) never
aborts the pull: Odoo reads whatever finAPI has cached and the consent-expiry cron warns you.

**Late-arriving transactions:** banks routinely add a booking with a _past_ booking date after the import cursor has
already moved on (an evening transfer, a weekend booking posted on Monday, a pending item that becomes booked). To avoid
silently missing those, each scheduled pull also re-fetches the **last N days** (`Re-check last N days`, default 7).
Already-imported lines are skipped by their unique import id, so this never creates duplicates. Set it to 0 to disable.

Manual / on-demand:

- Click **Refresh data now** on the provider to bypass the throttle and fetch + import the very latest bookings
  immediately (useful to verify the setup).
- When the PSD2 consent eventually expires (up to 180 days), click **Renew consent** to re-authorise via the Web Form
  without losing the existing account link.
- If **Refresh data now** hits an expired consent, finAPI answers "Web Form required" (SCA). That is not an error: Odoo
  shows a warning offering **Renew consent** right away, so you can re-authorise and repeat the refresh.
- The daily **finAPI: Check consent expiry** job emails a warning before the consent lapses.
