Some bank statement sources (e.g. some CSV/sheet exports or camt files) do
not provide a unique identifier for their transactions. Without it,
importing an overlapping period creates duplicate statement lines.

This module adds an option on bank journals to generate a
`unique_import_id` for statement lines that come without one. The value is
a SHA-256 hash of the normalized account number, date, payment reference,
amount, reference and partner name. An identifier provided by the source
always takes priority.

Identical transactions within the same import are numbered (`<hash>`,
`<hash>-2`, `<hash>-3`, ...), so they are all imported, while importing
the same statement again still ignores all of them.
