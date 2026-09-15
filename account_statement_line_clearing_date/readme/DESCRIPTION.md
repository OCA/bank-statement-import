This module adds a **clearing date** to bank statement lines. When set, the
clearing date drives the statement's order (`internal_index`) and balance
chain instead of the accounting date (without changing the accounting date).

Because `internal_index` keeps the standard format, the initial, ending and
running-balance computations stay correct: the delayed line's amount lands in
the statement where cleared, and each statement's starting balance matches the
previous' ending balance.
