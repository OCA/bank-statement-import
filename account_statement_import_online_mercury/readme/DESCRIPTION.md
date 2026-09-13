Connects Odoo to [Mercury](https://mercury.com) using the
[Mercury REST API](https://docs.mercury.com/reference/introduction) to automatically
pull bank statement lines into your accounting journals.

**Mercury** is a US business banking platform (checking, savings, treasury) built for
startups and small businesses. It offers a public REST API at
`https://api.mercury.com/api/v1` with Bearer token authentication. This module uses
the following endpoints:

- `GET /accounts` — list accounts (used for auto-detection)
- `GET /account/{id}/transactions` — fetch transactions with date filtering and
  cursor-based pagination

A **read-only API key** is sufficient for statement import. Read-only keys have no
IP allowlist requirement. Write-access keys (needed for the future Mercury Plus
invoicing feature) require IP allowlisting in *Mercury → Settings → API Keys*.
