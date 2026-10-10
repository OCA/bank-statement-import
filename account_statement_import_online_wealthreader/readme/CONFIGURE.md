## Step 1: Get your Wealthreader API Key

1. Go to [www.wealthreader.com](https://www.wealthreader.com) and sign up for an
   account. You get a **free 60-day trial** with no commitment.
2. After registration you will receive an **API Key** (8 alphanumeric characters).
   Keep it safe — you will need it in the next step.

## Step 2: Configure the provider in Odoo

1. Navigate to **Invoicing / Accounting → Configuration → Bank Accounts**.
2. Select the bank account (journal) you want to connect.
3. Set **Bank Feeds** to **Online (OCA)**.
4. Click the link to open the **Online Bank Statement Provider** form.
5. Select **Wealthreader** as the service.
6. Fill in the following fields:

   | Field             | Description                                                                                                                                                |
   | ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | **API Key**       | Your Wealthreader API Key obtained in Step 1.                                                                                                              |
   | **Entity Code**   | The code of your bank as listed at [wealthreader.com/supported-entities](https://www.wealthreader.com/supported-entities/) (e.g. `caixabank`, `santander`). |
   | **Bank Username** | Your online banking username. Only needed for the first connection — after that a secure token is used automatically.                                       |
   | **Bank Password** | Your online banking password. Same as above — only used once to generate a token.                                                                          |
   | **Date Type**     | Choose *Value Date* (when funds are effective) or *Operation Date* (when the bank processed the operation). Default: *Value Date*.                          |

7. Click **Test Connection** to verify everything works.
8. On success, the **Account Code (IBAN)** field will be populated automatically,
   and a credential **token** will be stored so that future pulls no longer require
   your raw bank credentials.

## Step 3: Pull statements

- Use the **Online Bank Statements Pull Wizard** to import historical transactions
  for a specific date range.
- Enable the **Scheduled Activity** to pull new transactions automatically at your
  desired interval (daily, hourly, etc.).
