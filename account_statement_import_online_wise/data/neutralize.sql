-- disable wise
UPDATE online_bank_statement_provider
SET certificate_private_key = 'dummy',
    certificate_public_key = 'dummy'
WHERE service='transferwise';
