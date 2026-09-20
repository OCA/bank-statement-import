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
