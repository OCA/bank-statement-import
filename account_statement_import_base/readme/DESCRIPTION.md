This is a technical module designed to share code between 2 other
modules:

- **account_statement_import_file** that allows to import bank statements
  from files,
- **account_statement_import_online** that allows to import bank
  statements from webservices/APIs.

It also adds to the statement lines some details that many import
formats and online providers give about the counterpart and the payment,
beyond the standard fields (partner name, account number, transaction
type): email, phone and address of the counterpart, its reference at the
provider, payment method, masked card number and expiry date, merchant
category, subscription reference and a link to the transaction at the
provider. They are shown in the *Transaction Details* tab of the line.

When the raw data of a line is JSON, it is also copied to the standard
*transaction details* of the line, which Odoo shows in the bank
reconciliation.
