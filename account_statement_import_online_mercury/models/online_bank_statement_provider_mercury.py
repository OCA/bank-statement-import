# Copyright 2024 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import logging
from datetime import datetime, timezone

import requests

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

MERCURY_API_BASE = "https://api.mercury.com/api/v1"
# Mercury allows up to 500 results per page
_PAGE_LIMIT = 500


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    mercury_account_id = fields.Char(
        string="Mercury Account ID",
        help="The Mercury account UUID shown in the Mercury dashboard URL "
        "(e.g. https://app.mercury.com/accounts/<uuid>). "
        "Leave blank to import from all accounts (first account used).",
    )
    mercury_include_pending = fields.Boolean(
        string="Include Pending Transactions",
        default=False,
        help="If enabled, transactions with status 'pending' are included. "
        "They may be reversed or change amount before posting.",
    )

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("mercury", "Mercury"),
        ]

    # ------------------------------------------------------------------
    # Core hook
    # ------------------------------------------------------------------

    def _obtain_statement_data(self, date_since, date_until):
        """Fetch Mercury transactions and return (lines, {}) for the base module."""
        self.ensure_one()
        if self.service != "mercury":
            return super()._obtain_statement_data(date_since, date_until)

        _logger.info(
            "Mercury: fetching transactions for journal %s from %s to %s",
            self.journal_id.name,
            date_since,
            date_until,
        )
        transactions = self._mercury_fetch_transactions(date_since, date_until)
        lines = [self._mercury_transaction_to_line(t) for t in transactions]
        _logger.info("Mercury: got %d transactions", len(lines))
        return lines, {}

    # ------------------------------------------------------------------
    # API helpers
    # ------------------------------------------------------------------

    def _mercury_session(self):
        """Return a requests.Session pre-configured with Mercury auth headers."""
        api_key = self.password
        if not api_key:
            raise UserError(
                self.env._(
                    "Mercury API key is not configured. "
                    "Set it in the 'API Key / Password' field on the provider."
                )
            )
        # Mercury tokens must be sent as "secret-token:<token>" — normalize
        # whether the user pastes the full form or just the bare token.
        if not api_key.startswith("secret-token:"):
            api_key = f"secret-token:{api_key}"
        session = requests.Session()
        session.headers.update(
            {
                "Authorization": f"Bearer {api_key}",
                "Accept": "application/json",
            }
        )
        return session

    def _mercury_get(self, session, path, params=None):
        """GET from Mercury API; raise UserError on non-200."""
        url = f"{MERCURY_API_BASE}{path}"
        try:
            resp = session.get(url, params=params, timeout=30)
        except requests.RequestException as exc:
            raise UserError(
                self.env._("Mercury API request failed: %(error)s", error=str(exc))
            ) from exc
        if resp.status_code == 401:
            raise UserError(
                self.env._("Mercury API key is invalid or expired (HTTP 401).")
            )
        if not resp.ok:
            raise UserError(
                self.env._(
                    "Mercury API returned HTTP %(status)s: %(body)s",
                    status=resp.status_code,
                    body=resp.text[:400],
                )
            )
        return resp.json()

    def _mercury_resolve_account_id(self, session):
        """Return the Mercury account UUID to use for this provider."""
        if self.mercury_account_id:
            return self.mercury_account_id
        # Auto-detect: pick first account
        data = self._mercury_get(session, "/accounts")
        accounts = data.get("accounts", [])
        if not accounts:
            raise UserError(self.env._("No Mercury accounts found for this API key."))
        account_id = accounts[0]["id"]
        _logger.info(
            "Mercury: auto-selected account %s (%s)",
            accounts[0].get("name", ""),
            account_id,
        )
        return account_id

    def _mercury_fetch_transactions(self, date_since, date_until):
        """Return all transactions in [date_since, date_until] via cursor pagination."""
        session = self._mercury_session()
        account_id = self._mercury_resolve_account_id(session)

        def _fmt(dt):
            return dt.strftime("%Y-%m-%d") if hasattr(dt, "strftime") else str(dt)[:10]

        # Mercury date params are YYYY-MM-DD strings
        params = {
            "limit": _PAGE_LIMIT,
            "start": _fmt(date_since),
            "end": _fmt(date_until),
        }
        if not self.mercury_include_pending:
            params["status"] = "sent"

        path = f"/account/{account_id}/transactions"
        all_transactions = []

        while True:
            data = self._mercury_get(session, path, params=params)
            transactions = data.get("transactions", [])
            all_transactions.extend(transactions)

            # Cursor-based pagination — retain original filter params (date, status)
            next_cursor = data.get("page", {}).get("nextPage")
            if not next_cursor or len(transactions) < _PAGE_LIMIT:
                break
            params["offset"] = next_cursor

        return all_transactions

    # ------------------------------------------------------------------
    # Data mapping
    # ------------------------------------------------------------------

    def _mercury_transaction_to_line(self, transaction):
        """Map a Mercury transaction dict to an Odoo statement line dict."""
        amount = transaction.get("amount", 0.0)
        # Mercury uses positive for credits, negative for debits — matches Odoo sign
        # convention. Verify by checking bankDescription direction if needed.

        # Pick the best available date: postedAt > createdAt
        date_str = transaction.get("postedAt") or transaction.get("createdAt")
        date = self._mercury_parse_datetime(date_str)

        # Build reference from available description fields
        ref_parts = [
            transaction.get("bankDescription") or "",
            transaction.get("externalMemo") or "",
            transaction.get("note") or "",
        ]
        ref = " | ".join(p for p in ref_parts if p).strip() or "/"

        vals = {
            "date": date,
            "amount": amount,
            "ref": ref,
            "payment_ref": ref,
            "unique_import_id": transaction["id"],
            "raw_data": json.dumps(transaction),
        }

        counterparty_name = transaction.get("counterpartyName") or transaction.get(
            "counterpartyNickname"
        )
        if counterparty_name:
            vals["partner_name"] = counterparty_name

        account_number = transaction.get("counterpartyAccountNumber")
        if account_number:
            vals["account_number"] = account_number

        return vals

    @staticmethod
    def _mercury_parse_datetime(dt_str):
        """Parse Mercury ISO-8601 UTC timestamp to a naive local datetime."""
        if not dt_str:
            return datetime.now()
        # Handle both 'Z' suffix and '+00:00'
        dt_str = dt_str.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(dt_str)
        except ValueError:
            _logger.debug("Mercury: could not parse date %r, using now()", dt_str)
            return datetime.now()
        # Convert to UTC-naive for Odoo
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
