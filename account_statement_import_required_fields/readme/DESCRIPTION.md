This module allows you to enforce mandatory columns when importing bank statements via TXT/CSV/XLSX in Odoo. It extends the mapping profiles from the Odoo Community Association (OCA) module `account_statement_import_sheet_file`.

---

## Key Features

1. **Mandatory Column Configuration**
   - In your Bank Statement Sheet Mappings, you can designate specific mapped columns as "Mandatory Mapping Columns".
   - Only columns that you have mapped (e.g., Date, Description, Amount) will be available to select.
   - If a column is cleared from the mapping, it is automatically deselected from the mandatory fields list.

2. **Pre-Import Data Validation**
   - When importing a file, the parser intercepts the raw TXT/CSV/XLSX cells before Odoo processes them.
   - If any of the mandatory columns are completely empty or blank in the file for a particular line, the import is halted immediately.
   - Generates a clear, user-friendly error message detailing exactly which required columns are missing data.

3. **Smart Debit/Credit Amount Handling**
   - Bank statements often represent amounts by placing values exclusively in either a Debit column or a Credit column.
   - If you set **both** the *Debit amount column* and *Credit amount column* as mandatory, the module intelligently requires that **at least one** of them must have a value on any given row.
