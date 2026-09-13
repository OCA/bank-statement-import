Once configured, statement lines are created automatically in the linked
journal. Each line carries:

- **Date** — `user_transaction_time` (falls back to `settlement_date`),
  normalized to UTC.
- **Amount** — Ramp returns positive amounts on spend; the module flips the
  sign so spend lands as a negative line on the credit-line liability journal
  (matching the standard Odoo convention for bank-type journals).
- **Reference / Payment Reference** — `merchant_name` (falls back to
  `merchant_descriptor` then `memo`).
- **Partner name** — `merchant_name` when present (no `res.partner` is auto-
  created; reconcile rules can match against the name).
- **Raw data** — the full Ramp transaction payload as JSON, including
  `card_id`, `user_id`, `sk_category_name`, `accounting_categories`, and
  any other fields Ramp returns.

Transactions in state `DECLINED`, `PENDING_INITIATION`, or `ERROR` are
skipped — they do not post to the credit line and would otherwise produce
statement lines that need manual deletion.

Transactions are deduplicated by Ramp's transaction UUID, so pulling the
same date range twice will not create duplicate statement lines.
