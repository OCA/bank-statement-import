1. Ensure your user has the necessary permissions. Assign the user to the group "Technical / Show Full Accounting Features" to gain access to the required settings.
2. Go to "Invoicing" -> "Configuration" -> "Online Bank Statement Providers".
3. Configure the Provider

For more detailed information about the Stripe API and the balance transactions used by this module, please refer to the official Stripe documentation: https://docs.stripe.com/api/balance_transactions

If Odoo itself takes payments through Stripe (the Stripe payment
provider, for instance on the website), those payments are already
recorded by Odoo. To avoid importing them twice, check *Payments
Already Recorded by Odoo* (visible when the Payment module is
installed). For each transaction paid through Odoo:

- if its payment is posted on the account of this journal, the line of
  the payment is not imported (its fee is);
- otherwise the line is imported with the partner of the payment, ready
  to be reconciled with it.
