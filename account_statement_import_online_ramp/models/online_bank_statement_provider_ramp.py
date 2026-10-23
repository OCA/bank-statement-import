# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import logging
from base64 import b64encode
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

RAMP_HOSTS = {
    "production": "https://api.ramp.com",
    "sandbox": "https://demo-api.ramp.com",
}
# Scopes the module needs.
RAMP_SCOPES = "transactions:read users:read"
# Ramp's max page size is 100 (per developer docs).
_PAGE_SIZE = 100
# Refresh shortly before expiry to avoid 401s at the boundary.
_TOKEN_SAFETY_WINDOW = timedelta(seconds=60)
# Transactions in these states are not posted to the credit line.
_SKIPPED_STATES = {"DECLINED", "PENDING_INITIATION", "ERROR"}
# Defence in depth against a runaway cursor loop.
_MAX_PAGES = 1000
# Per-request HTTP timeout (seconds).
_HTTP_TIMEOUT = 30
# Retry strategy for transient Ramp failures. Idempotent calls only.
_RETRY_TOTAL = 3
_RETRY_BACKOFF = 0.5


def _utcnow_naive():
    """Return a timezone-naive UTC datetime."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_retry_adapter():
    """HTTP adapter with backoff on transient 5xx + connection errors."""
    retry = Retry(
        total=_RETRY_TOTAL,
        backoff_factor=_RETRY_BACKOFF,
        status_forcelist=(502, 503, 504),
        allowed_methods=frozenset(("GET", "POST")),
        raise_on_status=False,
    )
    return HTTPAdapter(max_retries=retry)


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    ramp_host = fields.Selection(
        [("sandbox", "Sandbox"), ("production", "Production")],
        string="Ramp Environment",
        default="sandbox",
        help="Sandbox uses demo-api.ramp.com; Production uses api.ramp.com.",
    )
    ramp_access_token = fields.Char(
        help="Cached OAuth2 bearer token. Refreshed automatically on expiry "
        "or on HTTP 401. Should not normally be edited by hand.",
    )
    ramp_token_expiry = fields.Datetime(
        help="UTC expiry of the cached bearer token.",
    )

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [("ramp", "Ramp")]

    # ------------------------------------------------------------------
    # Core hook
    # ------------------------------------------------------------------

    def _obtain_statement_data(self, date_since, date_until):
        """Fetch Ramp transactions and return (lines, {}) for the base module."""
        self.ensure_one()
        if self.service != "ramp":
            return super()._obtain_statement_data(date_since, date_until)

        _logger.info(
            "Ramp: fetching transactions for journal %s from %s to %s",
            self.journal_id.name,
            date_since,
            date_until,
        )
        transactions = self._ramp_fetch_transactions(date_since, date_until)
        lines = [
            self._ramp_transaction_to_line(t)
            for t in transactions
            if t.get("state") not in _SKIPPED_STATES
        ]
        _logger.info("Ramp: produced %d statement lines", len(lines))
        return lines, {}

    # ------------------------------------------------------------------
    # OAuth2 token management
    # ------------------------------------------------------------------

    def _ramp_base_url(self):
        host = RAMP_HOSTS.get(self.ramp_host or "sandbox")
        if not host:
            raise UserError(
                _("Unknown Ramp environment: %(host)s") % {"host": self.ramp_host}
            )
        return host

    def _ramp_token_is_valid(self):
        """True iff cached token exists and is not within the safety window."""
        if not self.ramp_access_token or not self.ramp_token_expiry:
            return False
        return self.ramp_token_expiry > _utcnow_naive() + _TOKEN_SAFETY_WINDOW

    def _ramp_fetch_access_token(self):
        """Mint a fresh bearer via OAuth2 client_credentials."""
        self.ensure_one()
        # Serialise concurrent refreshes on the same provider row.
        self.env.cr.execute(
            "SELECT id FROM online_bank_statement_provider " "WHERE id = %s FOR UPDATE",
            (self.id,),
        )
        # Re-read whatever the lock holder may have just written.
        self.invalidate_recordset(["ramp_access_token", "ramp_token_expiry"])
        if self._ramp_token_is_valid():
            return self.ramp_access_token

        client_id = self.username
        client_secret = self.password
        if not client_id or not client_secret:
            raise UserError(
                _(
                    "Ramp client_id and client_secret must be set on the "
                    "provider (Username and Password fields)."
                )
            )
        creds = b64encode(f"{client_id}:{client_secret}".encode()).decode()
        url = f"{self._ramp_base_url()}/developer/v1/token"
        try:
            with requests.Session() as session:
                session.mount("https://", _build_retry_adapter())
                resp = session.post(
                    url,
                    headers={
                        "Authorization": f"Basic {creds}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                    },
                    data={"grant_type": "client_credentials", "scope": RAMP_SCOPES},
                    timeout=_HTTP_TIMEOUT,
                )
        except requests.RequestException as exc:
            raise UserError(
                _("Ramp token request failed: %(error)s") % {"error": str(exc)}
            ) from exc
        if resp.status_code in (401, 403):
            raise UserError(
                _(
                    "Ramp rejected the client credentials (HTTP %(status)s). "
                    "Verify client_id, client_secret, and that the OAuth2 app "
                    "is enabled for environment %(env)s."
                )
                % {"status": resp.status_code, "env": self.ramp_host}
            )
        if not resp.ok:
            raise UserError(
                _("Ramp token request returned HTTP %(status)s: %(body)s")
                % {"status": resp.status_code, "body": resp.text[:400]}
            )
        payload = resp.json()
        token = payload.get("access_token")
        # ``or`` so a null or 0 in the response also falls back.
        expires_in = int(payload.get("expires_in") or 7200)
        if not token:
            raise UserError(_("Ramp token response missing access_token field."))
        self.write(
            {
                "ramp_access_token": token,
                "ramp_token_expiry": _utcnow_naive() + timedelta(seconds=expires_in),
            }
        )
        return token

    def _ramp_get_access_token(self):
        """Return a usable bearer, minting a fresh one if the cache is stale."""
        if self._ramp_token_is_valid():
            return self.ramp_access_token
        return self._ramp_fetch_access_token()

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _ramp_session(self):
        token = self._ramp_get_access_token()
        session = requests.Session()
        session.mount("https://", _build_retry_adapter())
        session.headers.update(
            {
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
            }
        )
        return session

    def _ramp_assert_safe_url(self, url):
        """Reject any URL that is not HTTPS on the configured Ramp host."""
        expected = urlparse(self._ramp_base_url()).hostname
        parsed = urlparse(url)
        if parsed.scheme != "https" or parsed.hostname != expected:
            raise UserError(
                _(
                    "Ramp returned a URL pointing to an unexpected host "
                    "(%(actual)s, expected %(expected)s). Refusing to "
                    "follow it."
                )
                % {"actual": parsed.hostname or "<empty>", "expected": expected}
            )

    def _ramp_get(self, session, url, params=None):
        """GET from Ramp."""
        if not url.startswith("http"):
            url = f"{self._ramp_base_url()}{url}"
        else:
            self._ramp_assert_safe_url(url)
        try:
            resp = session.get(url, params=params, timeout=_HTTP_TIMEOUT)
        except requests.RequestException as exc:
            raise UserError(
                _("Ramp API request failed: %(error)s") % {"error": str(exc)}
            ) from exc
        if resp.status_code == 401:
            # Token expired or revoked — drop cache, mint new, retry once.
            self.write({"ramp_access_token": False, "ramp_token_expiry": False})
            new_token = self._ramp_get_access_token()
            session.headers["Authorization"] = f"Bearer {new_token}"
            try:
                resp = session.get(url, params=params, timeout=_HTTP_TIMEOUT)
            except requests.RequestException as exc:
                raise UserError(
                    _("Ramp API request failed after token refresh: %(error)s")
                    % {"error": str(exc)}
                ) from exc
        if not resp.ok:
            raise UserError(
                _("Ramp API returned HTTP %(status)s: %(body)s")
                % {"status": resp.status_code, "body": resp.text[:400]}
            )
        return resp.json()

    # ------------------------------------------------------------------
    # Transactions
    # ------------------------------------------------------------------

    def _ramp_fetch_transactions(self, date_since, date_until):
        """Return all Ramp card transactions in [date_since, date_until]."""
        session = self._ramp_session()

        def _fmt(dt):
            # Ramp accepts ISO 8601 with timezone. Normalize to UTC.
            if hasattr(dt, "isoformat"):
                if getattr(dt, "tzinfo", None) is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc).isoformat()
            return str(dt)

        url = "/developer/v1/transactions"
        params = {
            "from_date": _fmt(date_since),
            "to_date": _fmt(date_until),
            "page_size": _PAGE_SIZE,
        }
        all_transactions = []
        for _page in range(_MAX_PAGES):
            data = self._ramp_get(session, url, params=params)
            page = data.get("data") or []
            all_transactions.extend(page)
            next_url = (data.get("page") or {}).get("next")
            if not next_url:
                return all_transactions
            # The cursor URL already carries the filters.
            url = next_url
            params = None
        raise UserError(
            _(
                "Ramp pagination did not terminate after %(max)d pages. "
                "Aborting to avoid an unbounded loop."
            )
            % {"max": _MAX_PAGES}
        )

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def _ramp_transaction_to_line(self, txn):
        """Map a Ramp transaction dict to an Odoo statement line dict."""
        # Ramp is positive on spend; Odoo wants spend negative.
        amount = -float(txn.get("amount", 0.0))
        date = self._ramp_parse_datetime(
            txn.get("user_transaction_time") or txn.get("settlement_date")
        )
        merchant = (
            txn.get("merchant_name")
            or txn.get("merchant_descriptor")
            or txn.get("memo")
            or "/"
        )
        vals = {
            "date": date,
            "amount": amount,
            "ref": merchant,
            "payment_ref": merchant,
            "unique_import_id": txn["id"],
            # Keep the payload for downstream automation.
            "raw_data": json.dumps(txn),
        }
        if txn.get("merchant_name"):
            vals["partner_name"] = txn["merchant_name"]
        return vals

    @staticmethod
    def _ramp_parse_datetime(dt_str):
        """Parse a Ramp ISO 8601 timestamp to a naive UTC datetime."""
        if not dt_str:
            return _utcnow_naive()
        dt_str = dt_str.replace("Z", "+00:00")
        try:
            dt = datetime.fromisoformat(dt_str)
        except ValueError:
            _logger.debug("Ramp: could not parse date %r, using utcnow()", dt_str)
            return _utcnow_naive()
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt
