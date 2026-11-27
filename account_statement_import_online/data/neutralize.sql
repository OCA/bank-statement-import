-- disable online bank statement providers
UPDATE online_bank_statement_provider
   SET active = false;
