This module imports the transactions of [Soldo](https://www.soldo.com)
prepaid cards and wallets as bank statement lines, through the Soldo
Business API.

Each transaction becomes a line with:

- the merchant as label and counterpart name;
- the Soldo transaction id as reference, and the category of the
  transaction (payment, refund, top-up...) as transaction type;
- the notes of the transaction and of the card user as notes;
- the amount and currency of the payment, when it was made in a currency
  other than the one of the wallet;
- the whole transaction, as returned by Soldo, in the raw data.

A transaction with a fee gives a second line, with the fee.

The details of the transaction (card, merchant, merchant category, expense
category, notes, dates, original amount, fee and a link to the transaction in
Soldo) are logged in the chatter of the journal entry of the line.

Transactions can be imported once settled, on their settlement date and with
their final amount, or as soon as they are authorised. Wallets can be
excluded from the import, for instance the company wallet that tops up the
cards.

The receipts and invoices attached to the transactions in Soldo can be
imported too: they are attached to the journal entries of the statement lines.
Files are often attached in Soldo days after the payment: attaching a file
changes the transaction, so each pull also looks for the transactions changed
during the period, and adds the files that their lines do not have yet.

The transactions changed in Soldo after their import, for instance an
authorisation settled with a different amount, or an expense category or a
note added later, can update their statement lines. The label and the amount
of a line are updated only while it is not reconciled; a reconciled line whose
amount changed, and a line whose transaction was cancelled, are reported on
the provider, to be checked by hand.

Soldo does not give the balance of a wallet at a past date, so the
statements have no starting and ending balance.
