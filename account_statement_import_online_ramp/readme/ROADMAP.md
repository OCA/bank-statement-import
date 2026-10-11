- **Per-card journal routing** — for organizations with multiple credit lines
  or that want per-card analytic attribution at the journal level, allow a
  provider field to filter the transaction pull to a list of Ramp card UUIDs
  (or by card last-4).
- **Cardholder as a first-class field** — add `ramp_card_last_four` and
  `ramp_cardholder_user_id` (M2O `res.users`) to `account.bank.statement.line`
  in a companion module so cardholder is queryable/groupable in standard
  reports without parsing `raw_data`.
- **Reimbursements / bills** — extend coverage to `/developer/v1/reimbursements`
  and `/developer/v1/bills` for organizations that use Ramp's full
  spend-management feature set.
- **Webhook ingestion** — Ramp supports webhook delivery; a webhook receiver
  would deliver near-real-time statement lines instead of polling on cron.
