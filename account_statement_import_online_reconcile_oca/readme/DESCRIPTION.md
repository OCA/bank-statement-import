This module is a glue module between two modules:

- **account_statement_import_online** from
  [OCA/bank-statement-import](https://github.com/OCA/bank-statement-import).
- **account_reconcile_oca** from
  [OCA/account-reconcile](https://github.com/OCA/account-reconcile).

This module updates the accounting dashboard so that clicking **Transactions**
for a credit card opens the transaction reconciliation view when the online
provider's **Create Statement** option is disabled. When the option is enabled,
the existing Credit Statements behavior is preserved.
