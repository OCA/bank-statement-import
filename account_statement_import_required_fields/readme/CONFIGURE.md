This document explains how to configure mandatory columns for your bank statement imports.

---

## Configuring Mandatory Columns

To enforce that specific mapped columns are present during bank statement imports:

1. Go to **Accounting > Configuration > Statement Sheet Mappings** (or **Invoicing > Configuration > Statement Sheet Mappings** depending on your installed apps).
2. Open an existing mapping profile or create a new one according to your bank's file format.
3. Under the **Columns** section, fill in the names/indexes of the columns you are mapping (e.g., `Timestamp Column` = Date, `Amount column` = Amount).
4. Locate the **Required Fields** (or **Mandatory Mapping Columns**) section on the form.
5. Click to add fields. *Note: Only columns that you have mapped in step 3 will appear as available options.*
6. Select all the columns that you want to enforce as mandatory for every row in the imported file.

---

## Special Configuration: Debit and Credit Columns

If your bank statement format splits amounts into separate Debit and Credit columns rather than a single Amount column, you can enforce them intelligently:

1. Map both **Debit amount column** and **Credit amount column** in the Columns section.
2. Add **both** of them to the **Mandatory Mapping Columns** field.
3. **Result**: The module understands that a transaction is usually either a debit or a credit. During import, the parser will verify that **at least one** of these two fields has a value on every single row. If a row is entirely blank for both debit and credit, the import will be safely halted.
