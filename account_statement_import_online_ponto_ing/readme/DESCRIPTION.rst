This module provides special handling for Bank Transactions imported from Ponto
for the Dutch ING bank. Specifically it removes unneeded information from the
reference field (filled from the remittanceInformation) that is also provided in
other fields, like the counterpart accountnumber (IBAN) en the partnername.
