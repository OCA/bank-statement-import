To configure online bank statements provider:

1.  Go to *Invoicing \> Configuration \> Bank Accounts*
2.  Open bank account to configure and edit it
3.  Set *Bank Feeds* to *Online*
4.  Select *Plaid.com* as online bank statements provider in *Online
    Bank Statements (OCA)* section
5.  Save the bank account
6.  Click on provider and configure provider-specific settings.

or, alternatively:

1.  Go to *Invoicing \> Overview*
2.  Open settings of the corresponding journal account
3.  Switch to *Bank Account* tab
4.  Set *Bank Feeds* to *Online*
5.  Select *Plaid.com* as online bank statements provider in *Online
    Bank Statements (OCA)* section
6.  Save the bank account
7.  Click on provider and configure provider-specific settings.

## Plaid Account & Credentials

To obtain the necessary credentials (*Client ID* and *Secret*), follow
these steps:

1.  **Create a Plaid Account**: Go to
    [dashboard.plaid.com/signup](https://dashboard.plaid.com/signup) and
    sign up for a developer account.

2.  **Get Credentials**: Once logged in, navigate to **Platform \>
    Developers \> Keys** in the Plaid Dashboard. Here you will find your
    **Client ID** and **Secret**.

    ![Plaid Keys Dashboard](../static/description/plaid_keys.png)

    > [!NOTE]
    > There are different secrets for **Sandbox** (testing) and
    > **Production** (live) environments. Make sure to copy the secret
    > corresponding to the environment you intend to use.

    > [!IMPORTANT]
    > **Account Approval Times:**
    >
    > - For **US-based companies**, approval typically takes **1-2
    >   business days**.
    > - For **companies outside the United States**, the approval
    >   process may take longer.

## Configuration in Odoo

When configuring the provider in Odoo, map the Plaid credentials as
follows:

- **Username**: Enter your Plaid **Client ID**.
- **Password**: Enter your Plaid **Secret** (Sandbox or Production).
- **Plaid Environment**: Select **Sandbox** for testing or
  **Production** for live data.

Check also `account_bank_statement_import_online` configuration
instructions for more information.
