 This module allows you to import CAMT.054 file (details of customers payments batch) into a dedicated journal taking care of the start/end balance and the remittance reference number.

Customer invoices will be reconciled/Paid. Payment entries will be posted into an internal transfer account (that you have to create with a type current asset and set on the journal)

After this first step, import normally your CAMT.053 (full bank statement) into the bank journal. You will be able to clear the internal transfer account to end up the accounting flow.

Optionally we can activate add generation of additional line in bank statement which will balance your bank statement total to 0.
This line can be consolidated later with different account.
To enable option of final statement line you need properly set flag on Account Journal
Configuration -> Journals -> tab Advanced Settings -> Bank statement configuration


Switzerland localisation
------------------------

For ISR containing a partner reference, uses the config parameter key `isr_partner_ref`.
Doing so will fill the partners on bank statement lines and speed up the matches in the reconciliation process.

Value to set in `isr_partner_ref` defines the position of the partner reference inside the ISR.
The format is `i[,n]`
For instance `13,6` to start on position 13 with a 6 digit long reference.
`n` is optional and it's default value is `6`.
