* Only transactions for the previous three years are retrieved, historical data
  can be imported manually, see ``account_bank_statement_import_paypal``. See
  `PayPal Help Center article <https://www.paypal.com/us/smarthelp/article/why-can't-i-access-transaction-history-greater-than-3-years-ts2241>`_
  for details.
* `PayPal Transaction Info <https://developer.paypal.com/docs/api/sync/v1/#definition-transaction_info>`_
  defines extra fields like ``tip_amount``, ``shipping_amount``, etc. that
  could be useful to be decomposed from a single transaction.
