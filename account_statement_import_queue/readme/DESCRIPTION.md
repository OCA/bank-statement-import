# Import Bank Statement History Module

This module allows users to import bank statements into Odoo efficiently while keeping a detailed **import history**. It inherits the core `account_statement_import_sheet_file` module and uses `queue_job` to process large files asynchronously.

---

## Key Features

1. **Batch Bank Statement Import**
   - Import large bank statement files in **batches**.
   - Each batch is processed as a separate **queue job**, controlled by the system parameter `import.bank.statement.line.batch.limit`.

2. **Import as Batch Button**
   - Click the **Import as Batch** button to trigger the import process.
   - The module automatically creates a **chain of queue jobs** to:
     1. Parse the statement file
     2. Prepare data for import
     3. Create bank statements
     4. Create statement lines in batches
     5. Update start and end balances
     6. Update result and state

3. **Bank Statement History Tracking**
   - All imports are stored in `Import Bank Statement History` for auditing and traceability.
   - Tracks:
     - File uploaded (`import_attachment_id`)
     - State (`draft`, `importing_data`, `done`, `import_data_error`, `cancel`)
     - Exception messages for failed imports
     - Related queue jobs
     - Related bank statement records created

4. **Exception Handling**
   - If an import fails, errors are logged in detail with traceback information.
   - Users can reset the record to draft and retry the import.
