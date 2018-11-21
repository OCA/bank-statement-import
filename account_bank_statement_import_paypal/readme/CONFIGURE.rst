In the menu Accounting > Configuration > Accounting > Bank Accounts,
make sure that you have your Paypal bank account with the following parameters:
* Bank Account Type: Normal Bank Account
* Account Number: the email address associated with your Paypal account
* Account Journal: the journal associated to your Paypal account

TIPS
----
For now only French and English report are supported.
For adding new support you just need to add your header in
model/account_bank_statement_import_paypal.py in the variables HEADERS.
Please help us and do a PR for adding new header ! Thanks
