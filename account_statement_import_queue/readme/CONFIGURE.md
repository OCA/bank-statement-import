# Bank Statement Import History - Configuration Guide

This document explains how to configure and use the **Bank Statement Import History** module for importing bank statements in batch using queue jobs.

---

## 1. Configure Statement Sheet Mapping

To map columns from TXT/CSV/XLSX statement files:

1. Go to **Invoicing > Configuration > Accounting > Statement Sheet Mappings**.
2. Create a new mapping according to your online banking software's statement format.
3. Ensure required fields such as **Date**, **Amount**, **Transaction Reference**, and **Bank Account Number** are correctly mapped.
4. Save the mapping for later selection during import.

---

## 2. Configure Batch Limit

The module supports batch processing for statement lines.

- **System Parameter:** `import.bank.statement.line.batch.limit`
- **Default Value:** 100
- **Effect:** Determines the number of statement lines processed per queue job batch.
- **Recommendation:** 100–500 lines per batch depending on server capacity.

---

## 3. Upload Bank Statement File

1. Navigate to **Accounting > Bank and Cash > Import Statement**.
2. Select:
   - **Import File** – Upload your TXT, CSV, or XLSX file.
   - **Sheet Mapping** – Select the mapping created in Step 1.

---

## 3. Import as Batch

1. Click the **Import as Batch** button.
2. The system will automatically create a **queue job chain** to:
   - Parse the statement file.
   - Prepare statement data for import.
   - Create bank statements in Odoo.
   - Create statement lines in batches.
   - Update start and end balances.
   - Update import result and state.
3. The batch size is controlled by the system parameter: