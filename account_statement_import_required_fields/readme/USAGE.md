To use this module, follow these steps:

1. Export your bank statement from your online banking portal in **CSV** or **XLSX** or **TXT** format.
2. In Odoo, navigate to your Accounting Dashboard and click **Import Statement** on the relevant bank journal.
3. Upload your statement file and select the **Sheet Mapping** profile you configured with your Mandatory Columns.
4. Click **Import**.
5. **Validation in Action**: Odoo will scan the file before creating any records. If any row is missing data in one of the columns you marked as mandatory, the import will be safely halted. 
6. An error message will appear detailing exactly which required columns are missing data. Correct your file (or remove the junk row) and retry the import!
