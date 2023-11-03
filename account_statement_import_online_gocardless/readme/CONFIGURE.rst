On the GoCardless website
~~~~~~~~~~~~~~~~~~~~~~~~~

#. Go to https://bankaccountdata.gocardless.com, and create or login into your
   "GoCardLess Bank Account Data" account.
#. Go to Developers > User secrets option on the left.
#. Click on the "+ Create new" button on the bottom part.
#. Put a name to the user secret (eg. Odoo), and optionally limit it to certain
   IPs using CIDR subnet notation.
#. Copy or download the secret ID and key for later use. The second one won't be
   available anymore, so make sure you don't forget this step.

On Odoo
~~~~~~~

To configure online bank statements provider:

#. Add your user to the "Full Accounting Settings" group.
#. Go to *Invoicing > Configuration > Accounting > Journals*.
#. Select the journal representing your bank account (or create it).
#. The bank account number should be properly introduced.
#. Set *Bank Feeds* to *Online (OCA)*.
#. Select *GoCardless* as online bank statements provider in
   *Online Bank Statements (OCA)* section.
#. Save the journal
#. Click on the created provider.
#. Put your secret ID and secret key on the existing fields.
#. Click on the button "Select Bank Account Identifier".

   .. image:: ../static/img/gocardless_configuration.gif

#. A new window will appear for selecting the bank entity.

   .. image:: ../static/img/gocardless_bank_selection.gif

#. Select it, and you will be redirected to the selected entity for introducing
   your bank credentials to allow the connection.
#. If the process is completed, and the bank account linked to the journal is
   accessible, you'll be again redirected to the online provider form, and
   everything will be linked and ready to start the transaction pulling. A
   message is logged about it on the chatter.
#. If not, an error message will be logged either in the chatter.
