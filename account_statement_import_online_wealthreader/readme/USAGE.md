## Pulling historical statements

1. Open the bank journal and click **Online Bank Statements Pull Wizard**.
2. Set the **From** and **To** dates for the period you want to import.
3. Click **Pull**. Transactions will be imported and bank statements created
   according to the configured statement creation mode (daily / weekly / monthly).

## Automatic scheduled pulls

Once the provider is configured, Odoo's scheduled action will automatically pull
new transactions at the interval defined on the provider (e.g. every 4 hours).

You can adjust the pull frequency in the provider's **Update Interval** settings.

## Token-based security

After the first successful connection, Wealthreader returns a **credential token**.
This token is stored in Odoo and used for all subsequent requests, so your raw bank
username and password are never sent again. If you need to re-authenticate (e.g.
after changing your bank password), simply clear the token field and update the Bank
Username / Password, then pull again.

## Multiple accounts at the same bank

If your bank entity returns multiple accounts, the module matches the correct one
using the IBAN configured on the Odoo bank journal. Make sure the journal's bank
account number matches the IBAN of the account you want to import.

For additional accounts, create separate journals — each with its own provider
instance pointing to the same entity code but a different IBAN.
