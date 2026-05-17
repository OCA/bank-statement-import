This module adds a configuration field `Statement Line Internal Index` on bank
journals to allow changing the default computation of the `internal_index`
of bank statement lines.

The `internal_index` is used to order the statement lines.

When importing multiple bank statements for the same day, the default computation
does not work well; because the lines of each statement are mixed together.

Using the custom index computation `Statement together ...` statement lines from
the same statement are kept together.
