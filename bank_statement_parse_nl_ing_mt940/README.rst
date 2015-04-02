Import MT940 IBAN ING Bank Statements
=====================================

This module allows you to import the MT940 IBAN files from the Dutch ING bank
in Odoo as bank statements.
The specifications are published at:
    https://www.ing.nl/media/ING_ming_mt940s_24_juli_tcm162-46356.pdf
and were last updated august 2014.

Installation
============

This module is available:
* for Odoo version 8: in the OCA project bank-statement-import: 
  https://github.com/OCA/bank-statement-import

Configuration
=============

In the menu Accounting > Configuration > Accounts > Setup your Bank Accounts,
make sure that you have your ING bank account with the following parameters:

* Bank Account Type: Normal Bank Account
* Account Number: the bank account number also appearing in the statements
* Account Journal: the journal associated to your bank account
