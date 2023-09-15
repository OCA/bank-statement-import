This is a technical modules that you can use to improve the processing of
statement files from payment providers. These statements usually consist
of lines that to be reconciled by customer debts, offset by lines that are
to be reconciled by the imbursements from the payment provider, corrected
for customer credits and the costs of the payment provider. Typically, the
balance of such a statement is zero. Effectively, the counterpart of each
statement line is made on a clearing account and you should keep track of
the balance of the clearing account to see if the payment provider still owes
you money. You can keep track of the account by reconciling each entry on it.

That is where this module comes in. When importing such a statement, this
module reconciles all the counterparts on the clearing account with one
another. Reconciliation is executed when validating the statement. When
reopening the statement, the reconcilation is undone.

Known issues
============
This module does not come with its own tests because it depends on a
statement filter being installed. Instead, it is tested in
`account_bank_statement_import_adyen`
