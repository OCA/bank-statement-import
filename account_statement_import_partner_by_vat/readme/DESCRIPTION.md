`account_statement_import_base` matches the partner of a statement line
from the bank account number of the counterpart. Several statement
formats never carry that number: OFX is the main one, as `ofxparse`
exposes no counterpart account at all, so every line imported from an OFX
file is created without a partner.

This module adds a second matching pass for those formats: it looks for a
VAT number written in the label of the line and, when it finds one that
belongs to a partner, sets that partner on the line.

It applies to every import that goes through
`account.journal._statement_line_import_update_hook()`, which covers both
the file imports of `account_statement_import_file` (OFX, QIF, CAMT,
sheet) and the API imports of `account_statement_import_online`.
