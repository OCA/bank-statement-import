1. Ensure your user has the necessary permissions. Assign the user to the group "Technical / Show Full Accounting Features" to gain access to the required settings.
2. Go to "Invoicing" -> "Configuration" -> "Online Bank Statement Providers".
3. Configure the Provider

For more detailed information about the Stripe API and the balance transactions used by this module, please refer to the official Stripe documentation: https://docs.stripe.com/api/balance_transactions

To use the customer, the invoice or the subscription of the payments in
the labels (for instance `{customer.email}`, `{invoice.number}` or
`{subscription.id}`), check *Fetch Billing Data*. The module then asks
Stripe for these objects, once per pull for each of them, and keeps
them in the raw data of the lines. The source of the transactions must
be expanded, as it is by default (`data.source`). Both the API versions
before and after 2025-03-31.basil are supported, so the version of the
Stripe account does not need to be changed.
