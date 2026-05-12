## Generate Ramp API credentials

1. Log in to [Ramp](https://app.ramp.com) as an Owner or Admin and go to
   **Settings → Developer API**.
2. Click **Create new app**, give it a name (e.g. *Odoo statement import*),
   and select the OAuth2 grant type **Client credentials**.
3. Grant the scopes `transactions:read` and `users:read`. (`users:read` lets
   the cardholder name and email travel with each transaction in `raw_data`;
   it is read-only.)
4. Copy the **Client ID** and **Client Secret**. The secret is shown once —
   store it securely.

## Configure Odoo

1. Go to **Accounting → Configuration → Journals** and open or create a
   bank-type journal whose default account is your Ramp credit-line liability
   GL account.
2. In the **Online Synchronization** section, select **Ramp** as the service.
3. Paste your **Client ID** and **Client Secret**.
4. Set the **Ramp Environment** to *Sandbox* for `demo-api.ramp.com`
   (Ramp's developer sandbox) or *Production* for `api.ramp.com`.
5. Set the **Synchronization Frequency** and save.
6. Click **Pull Now** (or let the scheduled activity run) to import
   transactions.

The bearer token is minted automatically on the first pull and cached on the
provider record. It refreshes a minute before its declared expiry, and on any
HTTP 401 it is dropped and re-minted transparently.
