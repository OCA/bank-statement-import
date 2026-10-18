**Getting finAPI credentials**

finAPI has no self-service sign-up. Request a test access at <https://www.finapi.io/jetzt-testen/>: it is free for 30
days, you tick _Access & Add-ons_, and finAPI asks for a personal business e-mail address. finAPI then sends you two
sets of client credentials. This module needs the **app client** (client ID and client secret); the mandator admin
client is not used. Production access to `https://live.finapi.io` comes with separate credentials.

**Configuring the provider**

1. Go to _Invoicing → Configuration → Bank Accounts_.
2. Open the bank account you want to configure.
3. Set _Bank Feeds_ to **Online**.
4. Select **finAPI** as Online Bank Statements provider.
5. Save the bank account, then click the provider link.
6. In the _finAPI_ section, enter:

   - **finAPI Environment** — _Sandbox_ or _Live_. This fills in the Access API and Web Form URLs; override them only
     for a proxy.
   - **Client ID** / **Client Secret** — the app client credentials you received from finAPI.

7. Click **Create finAPI user** (once per provider).
8. Click **Add bank connection** to start the Web Form 2.0 wizard.

**Testing with the sandbox**

With sandbox credentials you can run the whole flow without a real bank account, against finAPI's test banks. In the web
form, pick one of them:

- **finAPI Test Bank** (BLZ `DEMO0001`): Onlinebanking-ID `demo`, PIN `demo`. When asked for a TAN, the answer is always
  `123456`.
- **finAPI Test Bank** without Strong Customer Authentication: Onlinebanking-ID `demo_no_msa`, PIN `demo_no_msa`.
- **finAPI Test Redirect Bank** (BLZ `DEMO0002`): Onlinebanking-ID `demo`, PIN `demo`; the authorisation runs through a
  redirect.

Each test bank provides two checking accounts and one savings account, and finAPI generates new transactions for them
every day, so the scheduled pull has fresh bookings to import. See
[finAPI Test Banks](https://documentation.finapi.io/access/finapi-test-banks) for the full list.
