Soldo uses its advanced authentication: besides the client id and secret,
every request is signed with a private key whose public key is registered in
Soldo.

1. Generate a 2048 bit RSA key pair:

   ``` shell
   openssl genrsa -out soldo_private.pem 2048
   openssl rsa -in soldo_private.pem -pubout -out soldo_public.pem
   ```

2. In the Soldo web app, go to "Integrations" -> "Business API", create an
   application and upload the public key, as described in the [Soldo API
   documentation](https://developer.soldo.com/docs/api-set-up). Soldo shows
   the client id, the client secret and the fingerprint token only once.

3. Ensure your user has the necessary permissions. Assign the user to the
   group "Technical / Show Full Accounting Features".

4. Go to "Invoicing" -> "Configuration" -> "Online Bank Statement
   Providers", create a provider with the service "Soldo" on the journal of
   the cards, and fill in the client id, the client secret, the fingerprint
   token and the content of `soldo_private.pem`.

5. Choose which transactions to import, and the wallets to exclude, if any.
   Check "Import Soldo Attachments" to download the files attached to the
   transactions.
   Check "Update Imported Soldo Transactions" to update the lines of the
   transactions changed in Soldo after their import.

A journal can collect the transactions of all the wallets in one currency,
or the transactions of some wallets only: the wallets of other journals are
then excluded.

To test with a Soldo sandbox account, create the credentials in its web app in
the same way, activate the developer mode and set
`https://api-demo.soldocloud.net` as API base.
