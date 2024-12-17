## On the GoCardless website

1.  Go to <https://bankaccountdata.gocardless.com>, and create or login
    into your "GoCardLess Bank Account Data" account.
2.  Go to Developers \> User secrets option on the left.
3.  Click on the "+ Create new" button on the bottom part.
4.  Put a name to the user secret (eg. Odoo), and optionally limit it to
    certain IPs using CIDR subnet notation.
5.  Copy or download the secret ID and key for later use. The second one
    won't be available anymore, so make sure you don't forget this step.

## On Odoo

To configure online bank statements provider:

1.  Add your user to the "Full Accounting Settings" group.

2.  Go to *Invoicing \> Configuration \> Accounting \> Journals*.

3.  Select the journal representing your bank account (or create it).

4.  The bank account number should be properly introduced.

5.  Set *Bank Feeds* to *Online (OCA)*.

6.  Select *GoCardless* as online bank statements provider in *Online
    Bank Statements (OCA)* section.

7.  Save the journal

8.  Click on the created provider.

9.  Put your secret ID and secret key on the existing fields.

10. Click on the button "Select Bank Account Identifier".

    ![image_01](../static/img/gocardless_configuration.gif)

11. A new window will appear for selecting the bank entity.

    ![image_02](../static/img/gocardless_bank_selection.gif)

12. Select it, and you will be redirected to the selected entity for
    introducing your bank credentials to allow the connection.

13. If the process is completed, and the bank account linked to the
    journal is accessible, you'll be again redirected to the online
    provider form, and everything will be linked and ready to start the
    transaction pulling. A message is logged about it on the chatter.

14. If not, an error message will be logged either in the chatter.
