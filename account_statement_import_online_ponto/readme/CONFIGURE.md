To configure online bank statements provider:

1.  Go to *Invoicing \> Configuration \> Bank Accounts*
2.  Open bank account to configure and edit it
3.  Set *Bank Feeds* to *Online*
4.  Select *MyPonto.com* as online bank statements provider in *Online
    Bank Statements (OCA)* section
5.  Save the bank account
6.  Click on provider and configure provider-specific settings.

or, alternatively:

1.  Go to *Invoicing \> Overview*
2.  Open settings of the corresponding journal account
3.  Switch to *Bank Account* tab
4.  Set *Bank Feeds* to *Online*
5.  Select *MyPonto.com* as online bank statements provider in *Online
    Bank Statements (OCA)* section
6.  Save the bank account
7.  Click on provider and configure provider-specific settings.

To obtain *Client ID* and *Client Secret*:

1.  Open [MyPonto.com](https://myponto.com/).
2.  If you are in test environment, enable "Sandbox" mode.
3.  Add "Custom integration" to obtain *Client ID* and *Client Secret* credentials.
4.  Add an account to the custom integration. You can select test accounts if you are 
    in sandbox mode. 
5.  The reference of this account should be the same as the *Account Number* of the 
    bank journal in Odoo.

Check also `account_bank_statement_import_online` configuration
instructions for more information.
