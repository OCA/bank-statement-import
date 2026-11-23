1. Ensure your user has the necessary permissions. Assign the user to the group "Technical / Show Full Accounting Features" to gain access to the required settings.
2. Go to "Invoicing" -> "Configuration" -> "Online Bank Statement Providers".
3. Configure the Provider

For more detailed information about the Stripe API and the balance transactions used by this module, please refer to the official Stripe documentation: https://docs.stripe.com/api/balance_transactions

Stripe keeps a balance for each currency of the account, and the
transactions are in the currency of their balance. A provider imports
the balance in the currency of its journal: to import the balance in
another currency, add a provider with the same key on a journal in that
currency. When a balance in another currency has transactions and no
provider imports it, a message on the provider says so.

A payment made in a currency other than the one of its balance (for
instance a payment in USD settled in EUR) is imported in the currency of
the balance. To also keep the amount and the currency of the payment on
the line, check *Payments in Foreign Currencies*.
