## Generate a Mercury API Key

1. Log in to [Mercury](https://app.mercury.com) and go to **Settings → API Keys**.
2. Click **Create API Key**, choose **Read-only** scope, and copy the key.
   The key is shown once; store it securely.

> Read-only keys have no IP allowlist requirement. Write-access keys require
> IP allowlisting and are only needed for future invoicing/payment features.

## Configure Odoo

1. Go to **Accounting → Configuration → Journals** and open or create a bank journal.
2. In the **Online Synchronization** section, select **Mercury** as the service.
3. Paste your **API Key**. You may paste the bare token or the full
   `secret-token:…` form — both are accepted.
4. Optionally paste your **Mercury Account ID** — the UUID in the Mercury dashboard
   URL (`https://app.mercury.com/accounts/<uuid>`). Leave blank to auto-detect the
   first account on the key. If you have multiple accounts under one API key (e.g.
   checking and savings), set this field to pull from a specific account.
5. Enable **Include Pending Transactions** if you want to see unposted transactions.
   Note: pending transactions may be reversed or change amount before settlement.
6. Set the **Synchronization Frequency** and save.
7. Click **Pull Now** (or let the scheduled activity run) to import transactions.
