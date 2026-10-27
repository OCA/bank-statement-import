You will need a *Client ID* and *Secret* from PayPal to communicate with
the PayPal API. To obtain your PayPal API *Client ID* and *Secret*:

1.  Open [PayPal Developer](https://developer.paypal.com/dashboard/).
2.  Login with your *PayPal for Business* account (upgrade your personal
    account to a Business Account, if required).
3.  Go to *Apps & Credentials* and switch to *Live*.
4.  Under *REST API apps*, click *Create App* to begin creating a new
    application.
5.  Enter a descriptive name for your app (e.g. *Odoo-Statements*) and
    click *Create App*.
6.  Copy the *Client ID* and *Secret* to use during provider
    configuration (instructions below).
7.  Under *Features*, uncheck all optional features except *Transaction
    Search*.
8.  Click *Save Changes*.

To configure PayPal as an online bank statement provider, you will need
to create a Bank Account & Journal that corresponds to your *PayPal for
Business* account, and then configure the *PayPal.com* provider with the
*Client ID* and *Secret* obtained above:

1.  Go to *Invoicing \> Configuration \> Banks \> Add a Bank Account*.
2.  In the *Account Number* field, enter some descriptive text for the
    account, such as the email address or *PayPal Merchant ID* of your
    *PayPal for Business* account. NOTE: This *Account Number* is not
    used in the authentication with PayPal's API, and is only used to
    distinguish this PayPal Bank Account/Journal from others you may
    have configured.
3.  Fill in the other fields for the Bank Account if desired, and then
    click *Create*.
4.  Go to *Invoicing \> Configuration \> Accounting \> Journals*.
5.  Open and *Edit* the Journal corresponding to the PayPal bank account
    (this Journal was created automatically when you created the Bank
    Account above.
6.  Set *Bank Feeds* to *Online (OCA)*.
7.  Select *PayPal.com* as the provider in the *Online Bank Statements
    (OCA)* section.
8.  *Save* the Journal.
9.  To configure provider-specific settings, click on the provider to
    open it and click *Edit*.
10. Fill in your desired *Configuration* and *Scheduled Pull* settings.
11. Leave the *API base* field empty, and fill in the *Client ID* and
    *Secret* from your PayPal Developer account.
12. Click *Save*.

NOTE: For development and testing purposes, you can create Sandbox
credentials associated with your *PayPal for Business* account. When
configuring the provider-specific settings, enter the following in the
*API base* field: <https://api.sandbox.paypal.com>

If Odoo itself takes payments through PayPal (the PayPal payment
provider, for instance on the website), those payments are already
recorded by Odoo. To avoid importing them twice, check *Payments
Already Recorded by Odoo* (visible when the Payment module is
installed). For each transaction paid through Odoo:

- if its payment is posted on the account of this journal, the line of
  the payment is not imported (its fee is);
- otherwise the line is imported with the partner of the payment, ready
  to be reconciled with it.

Odoo identifies a payment by its capture, until the webhook of the
PayPal payment provider replaces it with the order, which the
transactions do not mention. For those payments the captures are read
from the order, so the app of the provider needs access to the orders
of the account as well (the feature to accept payments), and not only
*Transaction Search*.

In the first case the lines of the statement no longer add up to the
balances given by PayPal, as the payments are recorded outside of the
statement. Posting the payments on an outstanding account, and then
reconciling the lines, keeps the statements complete.
