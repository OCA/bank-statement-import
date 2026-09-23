Once configured, statement lines are created automatically in the linked journal.
Each line carries:

- **Date** — `postedAt` timestamp (falls back to `createdAt` for pending transactions)
- **Amount** — negative for debits, positive for credits
- **Reference** — bank description, external memo, and note concatenated with ` | `
- **Partner name** — counterparty name from Mercury
- **Account number** — counterparty account number (used for ACH partner matching)

Transactions are deduplicated by Mercury's transaction UUID, so pulling the same
date range twice will not create duplicate statement lines.
