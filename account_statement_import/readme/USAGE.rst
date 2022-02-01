To import a statement file, go to the Invoicing dashboard: on a bank journal, you will see a button to import a statement. When you click on that button, a wizard will start and it will show the list of the supported file formats. Select the statement file that you want to import and click on the **Import** button. Odoo will create a new bank statement (or several if your statement file is a multi-account file).

If your statement file contains transactions that were already imported in Odoo, they will not be created a second time.

If the statement file contains information about the bank account number of the counter-part for some transactions (only a few statement file formats support that, in some countries) and that these bank account numbers exists on partners in Odoo, the partners will be set on the related statement lines.
