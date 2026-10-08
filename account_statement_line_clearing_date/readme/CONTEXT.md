In Odoo 18 a bank statement is ordered by computed field `first_line_index`,
which is the minimum `internal_index` among its lines. `internal_index` is
itself derived from each line's `date`.

For credit-card statement, a **delayed transaction** (purchased on, say, March
1st but cleared by the bank on May 31st) is imported with date = March 1. That
early line drags the whole May statement's `first_line_index` back to March,
before the April statement. The balance chain then breaks.

By adding the clearing date to the delayed transaction, this module decouples
the accounting impact from its chronological sequence. When a `clearing_date`
is specified, the line's `internal_index` is recomputed using this new date
instead of the standard accounting `date`. That makes the balance chain for
the statements correct again.
