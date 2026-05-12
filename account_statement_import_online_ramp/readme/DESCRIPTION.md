Connects Odoo to [Ramp](https://ramp.com) using the
[Ramp Developer API](https://docs.ramp.com/developer-api) to automatically
pull corporate-card transactions into your accounting journals as bank
statement lines.

**Ramp** is a US corporate-card and spend-management platform. A Ramp
organization has one credit line shared across all cards, billed as a single
monthly statement and paid via one ACH transfer. This module follows that
accounting reality: one Ramp credit line maps to **one** Odoo bank-type
journal, regardless of how many cards are issued under it.

The module uses these endpoints:

- `POST /developer/v1/token` — OAuth2 client_credentials, mints a short-lived
  bearer that is cached on the provider record and refreshed on expiry or 401.
- `GET /developer/v1/transactions` — paginated card-transaction feed filtered
  by date range; cursor pagination via the `page.next` field.

Cardholder, card, merchant category, and Ramp accounting-category metadata are
preserved in each statement line's `raw_data` field so downstream automation
(reconcile rules, server actions, custom reports) can use them without a
second API call.

## Reliability and security

- **Concurrent-safe token refresh** — the mint takes a `SELECT ... FOR UPDATE`
  on the provider row and re-checks the cached token after acquiring it, so two
  cron runs on the same provider cannot mint two separate bearers.
- **Transient-failure retry** — three attempts with exponential backoff on 502,
  503 and 504, applied to both the token mint and the transaction fetch. A 401
  is not retried; it triggers a single transparent re-mint instead.
- **Pagination host validation** — the cursor URL Ramp returns in `page.next` is
  checked to be HTTPS on the configured Ramp host before it is followed, so a
  tampered response cannot redirect the bearer token to another host. The check
  compares hostnames, so `api.ramp.com:443` and `API.Ramp.com` are accepted
  while `api.ramp.com@evil.com` is not.
- **Bounded pagination** — the fetch loop stops after 1000 pages and raises,
  rather than looping forever on a cursor that never terminates.
