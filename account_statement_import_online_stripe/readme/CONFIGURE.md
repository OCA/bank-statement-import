1. Ensure your user has the necessary permissions. Assign the user to the group "Technical / Show Full Accounting Features" to gain access to the required settings.
2. Go to "Invoicing" -> "Configuration" -> "Online Bank Statement Providers".
3. Configure the Provider

For more detailed information about the Stripe API and the balance transactions used by this module, please refer to the official Stripe documentation: https://docs.stripe.com/api/balance_transactions

To check the statements against the balance of the Stripe account, check
*Statement Balances*: the starting and ending balances of each statement
are set from the current balance of the account (available and pending)
less the net amounts of the later transactions, and Odoo shows the
statements whose lines do not match them. The balance and the later
transactions are read once for each pull.
