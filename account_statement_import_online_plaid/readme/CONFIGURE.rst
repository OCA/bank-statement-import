To configure online bank statements provider:

#. Go to *Invoicing > Configuration > Bank Accounts*
#. Open bank account to configure and edit it
#. Set *Bank Feeds* to *Online*
#. Select *Plaid.com* as online bank statements provider in
   *Online Bank Statements (OCA)* section
#. Save the bank account
#. Click on provider and configure provider-specific settings.

or, alternatively:

#. Go to *Invoicing > Overview*
#. Open settings of the corresponding journal account
#. Switch to *Bank Account* tab
#. Set *Bank Feeds* to *Online*
#. Select *Plaid.com* as online bank statements provider in
   *Online Bank Statements (OCA)* section
#. Save the bank account
#. Click on provider and configure provider-specific settings.

Plaid Account & Credentials
~~~~~~~~~~~~~~~~~~~~~~~~~~~

To obtain the necessary credentials (*Client ID* and *Secret*), follow these steps:

#. **Create a Plaid Account**:
   Go to `dashboard.plaid.com/signup <https://dashboard.plaid.com/signup>`_ and sign up for a developer account.

#. **Get Credentials**:
   Once logged in, navigate to **Platform > Developers > Keys** in the Plaid Dashboard.
   Here you will find your **Client ID** and **Secret**.

   .. image:: ../static/description/plaid_keys.png
      :alt: Plaid Keys Dashboard

   .. note::
      There are different secrets for **Sandbox** (testing) and **Production** (live) environments.
      Make sure to copy the secret corresponding to the environment you intend to use.

   .. important::
      **Account Approval Times:**

      * For **US-based companies**, approval typically takes **1-2 business days**.
      * For **companies outside the United States**, the approval process may take longer.

Configuration in Odoo
~~~~~~~~~~~~~~~~~~~~~

When configuring the provider in Odoo, map the Plaid credentials as follows:

* **Username**: Enter your Plaid **Client ID**.
* **Password**: Enter your Plaid **Secret** (Sandbox or Production).
* **Plaid Environment**: Select **Sandbox** for testing or **Production** for live data.

Check also ``account_bank_statement_import_online`` configuration instructions
for more information.
