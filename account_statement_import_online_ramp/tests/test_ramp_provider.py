# Copyright 2026 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, Mock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


def _utcnow():
    """Match the module's naive-UTC convention without using deprecated utcnow."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


SAMPLE_TOKEN = {
    "access_token": "ramp-test-bearer-001",
    "token_type": "Bearer",
    "expires_in": 7200,
    "scope": "transactions:read users:read",
}

SAMPLE_TXNS = {
    "data": [
        {
            "id": "txn-uuid-001",
            "amount": 42.50,
            "state": "CLEARED",
            "merchant_name": "Acme Coffee",
            "merchant_descriptor": "ACME COFFEE #4421",
            "user_transaction_time": "2026-03-01T14:30:00.000Z",
            "settlement_date": "2026-03-02",
            "card_id": "card-uuid-001",
            "user_id": "user-uuid-alice",
            "sk_category_name": "Restaurants",
        },
        {
            "id": "txn-uuid-002",
            "amount": 199.00,
            "state": "CLEARED",
            "merchant_name": "Cloudy Hosting Inc.",
            "merchant_descriptor": "CLOUDY*HOST",
            "user_transaction_time": "2026-03-05T09:15:00.000Z",
            "card_id": "card-uuid-002",
            "user_id": "user-uuid-bob",
            "sk_category_name": "Computer Services",
        },
        {
            "id": "txn-uuid-declined",
            "amount": 1000.00,
            "state": "DECLINED",
            "merchant_name": "Suspicious Co",
            "user_transaction_time": "2026-03-10T00:00:00.000Z",
        },
    ],
    "page": {"next": None},
}

# Two-page dataset for pagination tests
PAGE_1 = {
    "data": [
        {
            "id": f"txn-page1-{i:03d}",
            "amount": float(i + 1),
            "state": "CLEARED",
            "merchant_name": f"Merchant {i}",
            "user_transaction_time": "2026-03-01T00:00:00.000Z",
        }
        for i in range(100)
    ],
    "page": {
        "next": "https://demo-api.ramp.com/developer/v1/transactions?start=cursor-abc"
    },
}

PAGE_2 = {
    "data": [
        {
            "id": "txn-page2-001",
            "amount": 5.0,
            "state": "CLEARED",
            "merchant_name": "Last Merchant",
            "user_transaction_time": "2026-03-15T00:00:00.000Z",
        }
    ],
    "page": {"next": None},
}

_journal_seq = [0]


class TestRampProvider(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {"name": "Ramp Test Card", "type": "bank", "code": "RMPTEST"}
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "journal_id": cls.journal.id,
                "service": "ramp",
                "username": "test-client-id",
                "password": "test-client-secret",
                "ramp_host": "sandbox",
                "ramp_access_token": "preset-bearer",
                "ramp_token_expiry": _utcnow() + timedelta(hours=1),
            }
        )

    def _new_provider(self, **vals):
        """Create a provider with a fresh journal — journal_id is unique."""
        _journal_seq[0] += 1
        journal = self.env["account.journal"].create(
            {
                "name": f"Ramp Test {_journal_seq[0]}",
                "type": "bank",
                "code": f"RMP{_journal_seq[0]:02d}",
            }
        )
        base = {
            "journal_id": journal.id,
            "service": "ramp",
            "username": "test-client-id",
            "password": "test-client-secret",
            "ramp_host": "sandbox",
            "ramp_access_token": "preset-bearer",
            "ramp_token_expiry": _utcnow() + timedelta(hours=1),
        }
        base.update(vals)
        return self.env["online.bank.statement.provider"].create(base)

    @staticmethod
    def _mock_get(session, url, params=None):
        """Side-effect for _ramp_get: dispatch by URL."""
        if "/developer/v1/transactions" in url:
            return SAMPLE_TXNS
        return {}

    # ------------------------------------------------------------------
    # Service registration
    # ------------------------------------------------------------------

    def test_service_registered(self):
        services = dict(self.provider._get_available_services())
        self.assertIn("ramp", services)

    # ------------------------------------------------------------------
    # Core data fetch + state filtering
    # ------------------------------------------------------------------

    def test_obtain_statement_data_drops_declined(self):
        date_since = datetime(2026, 3, 1)
        date_until = datetime(2026, 3, 31)
        with patch.object(type(self.provider), "_ramp_get", side_effect=self._mock_get):
            lines, meta = self.provider._obtain_statement_data(date_since, date_until)
        # 3 fixtures, 1 declined → 2 lines
        self.assertEqual(len(lines), 2)
        self.assertEqual(meta, {})
        ids = {line["unique_import_id"] for line in lines}
        self.assertEqual(ids, {"txn-uuid-001", "txn-uuid-002"})

    def test_obtain_statement_data_delegates_non_ramp(self):
        date_since = datetime(2026, 3, 1)
        date_until = datetime(2026, 3, 31)
        dummy = self._new_provider(service="dummy")
        result = dummy._obtain_statement_data(date_since, date_until)
        self.assertIsNotNone(result)

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_pagination_fetches_all_pages(self):
        call_count = [0]

        def _paged_get(session, url, params=None):
            call_count[0] += 1
            if call_count[0] == 1:
                return PAGE_1
            return PAGE_2

        with patch.object(type(self.provider), "_ramp_get", side_effect=_paged_get):
            txns = self.provider._ramp_fetch_transactions(
                datetime(2026, 3, 1), datetime(2026, 3, 31)
            )
        self.assertEqual(len(txns), 101)
        self.assertEqual(call_count[0], 2)

    def test_pagination_uses_next_url_without_params(self):
        """Page 2 must use the cursor URL as-is and pass params=None.

        Ramp's `next` URL already contains the encoded filters; re-sending
        `params` would double-encode them.
        """
        captured = []

        def _capture_get(session, url, params=None):
            captured.append((url, params))
            if len(captured) == 1:
                return PAGE_1
            return PAGE_2

        with patch.object(type(self.provider), "_ramp_get", side_effect=_capture_get):
            self.provider._ramp_fetch_transactions(
                datetime(2026, 3, 1), datetime(2026, 3, 31)
            )

        self.assertEqual(len(captured), 2)
        # First call: relative path + params dict with from_date/to_date/page_size
        first_url, first_params = captured[0]
        self.assertEqual(first_url, "/developer/v1/transactions")
        self.assertIn("from_date", first_params)
        self.assertIn("to_date", first_params)
        self.assertEqual(first_params["page_size"], 100)
        # Second call: full cursor URL + params=None
        second_url, second_params = captured[1]
        self.assertTrue(second_url.startswith("https://demo-api.ramp.com"))
        self.assertIn("start=cursor-abc", second_url)
        self.assertIsNone(second_params)

    # ------------------------------------------------------------------
    # Mapping
    # ------------------------------------------------------------------

    def test_transaction_mapping_flips_sign(self):
        txn = SAMPLE_TXNS["data"][0]
        line = self.provider._ramp_transaction_to_line(txn)
        self.assertEqual(line["unique_import_id"], "txn-uuid-001")
        # Ramp 42.50 spend → -42.50 on a CC liability journal
        self.assertAlmostEqual(line["amount"], -42.50)
        self.assertEqual(line["partner_name"], "Acme Coffee")
        self.assertEqual(line["ref"], "Acme Coffee")
        self.assertIsInstance(line["date"], datetime)
        # raw_data preserves cardholder/card so downstream automation can use it
        import json as _json

        raw = _json.loads(line["raw_data"])
        self.assertEqual(raw["card_id"], "card-uuid-001")
        self.assertEqual(raw["user_id"], "user-uuid-alice")

    def test_transaction_mapping_no_merchant(self):
        txn = {
            "id": "txn-empty",
            "amount": 1.0,
            "user_transaction_time": "2026-03-01T00:00:00.000Z",
        }
        line = self.provider._ramp_transaction_to_line(txn)
        self.assertEqual(line["ref"], "/")
        self.assertNotIn("partner_name", line)

    # ------------------------------------------------------------------
    # Datetime parsing
    # ------------------------------------------------------------------

    def test_parse_datetime_z_suffix(self):
        dt = self.provider._ramp_parse_datetime("2026-03-15T14:30:00.000Z")
        self.assertIsInstance(dt, datetime)
        self.assertIsNone(dt.tzinfo)

    def test_parse_datetime_offset(self):
        dt = self.provider._ramp_parse_datetime("2026-03-15T14:30:00+00:00")
        self.assertIsInstance(dt, datetime)
        self.assertIsNone(dt.tzinfo)

    def test_parse_datetime_none(self):
        dt = self.provider._ramp_parse_datetime(None)
        self.assertIsInstance(dt, datetime)

    def test_parse_datetime_malformed_falls_back_to_now(self):
        dt = self.provider._ramp_parse_datetime("not-a-date")
        self.assertIsInstance(dt, datetime)

    # ------------------------------------------------------------------
    # OAuth2 token cache
    # ------------------------------------------------------------------

    def test_token_cache_hit(self):
        """A valid cached token short-circuits the network call."""
        provider = self._new_provider(
            ramp_access_token="cached-bearer",
            ramp_token_expiry=_utcnow() + timedelta(hours=1),
        )
        with patch.object(type(provider), "_ramp_fetch_access_token") as mock_fetch:
            token = provider._ramp_get_access_token()
        mock_fetch.assert_not_called()
        self.assertEqual(token, "cached-bearer")

    def test_token_cache_miss_when_expired(self):
        """A token within the safety window is treated as stale."""
        provider = self._new_provider(
            ramp_access_token="stale-bearer",
            # 30s left — inside the 60s safety window
            ramp_token_expiry=_utcnow() + timedelta(seconds=30),
        )
        with patch.object(
            type(provider),
            "_ramp_fetch_access_token",
            return_value="fresh-bearer",
        ) as mock_fetch:
            token = provider._ramp_get_access_token()
        mock_fetch.assert_called_once()
        self.assertEqual(token, "fresh-bearer")

    def test_token_cache_miss_when_blank(self):
        provider = self._new_provider(ramp_access_token=False, ramp_token_expiry=False)
        with patch.object(
            type(provider),
            "_ramp_fetch_access_token",
            return_value="fresh-bearer",
        ) as mock_fetch:
            token = provider._ramp_get_access_token()
        mock_fetch.assert_called_once()
        self.assertEqual(token, "fresh-bearer")

    def _mock_session_with_response(self, mock_resp):
        """Build a MagicMock that mimics ``with requests.Session() as session``.

        ``requests.Session`` is used as a context manager in the token mint
        path, so the patched factory must return an object whose ``__enter__``
        yields itself (and whose ``.post`` returns the supplied response).
        """
        mock_session = MagicMock()
        mock_session.__enter__.return_value = mock_session
        mock_session.__exit__.return_value = False
        mock_session.post.return_value = mock_resp
        return mock_session

    def test_fetch_token_persists_to_record(self):
        """Successful token mint writes access_token + expiry back to the row."""
        provider = self._new_provider(ramp_access_token=False, ramp_token_expiry=False)
        mock_resp = Mock(ok=True, status_code=200)
        mock_resp.json.return_value = SAMPLE_TOKEN
        mock_session = self._mock_session_with_response(mock_resp)
        _SESSION = (
            "odoo.addons.account_statement_import_online_ramp"
            ".models.online_bank_statement_provider_ramp.requests.Session"
        )
        with patch(_SESSION, return_value=mock_session):
            token = provider._ramp_fetch_access_token()
        self.assertEqual(token, "ramp-test-bearer-001")
        self.assertEqual(provider.ramp_access_token, "ramp-test-bearer-001")
        self.assertGreater(provider.ramp_token_expiry, _utcnow())

    def test_fetch_token_missing_credentials_raises(self):
        # Empty cache so the credential check is reached — _ramp_fetch_access_token
        # short-circuits on a valid cached token (post-lock double-check).
        provider = self._new_provider(
            username=False,
            password=False,
            ramp_access_token=False,
            ramp_token_expiry=False,
        )
        with self.assertRaises(UserError):
            provider._ramp_fetch_access_token()

    def test_fetch_token_rejected_credentials_raises(self):
        provider = self._new_provider(ramp_access_token=False, ramp_token_expiry=False)
        mock_resp = Mock(ok=False, status_code=401, text="Unauthorized")
        mock_session = self._mock_session_with_response(mock_resp)
        _SESSION = (
            "odoo.addons.account_statement_import_online_ramp"
            ".models.online_bank_statement_provider_ramp.requests.Session"
        )
        with patch(_SESSION, return_value=mock_session):
            with self.assertRaises(UserError) as ctx:
                provider._ramp_fetch_access_token()
        self.assertIn("401", str(ctx.exception))

    # ------------------------------------------------------------------
    # _ramp_get — error handling and 401 retry
    # ------------------------------------------------------------------

    def test_get_401_refreshes_token_and_retries(self):
        """A 401 on a data call drops the cache, mints fresh, retries once."""
        provider = self._new_provider()
        first_resp = Mock(ok=False, status_code=401, text="Token expired")
        second_resp = Mock(ok=True, status_code=200)
        second_resp.json.return_value = {"data": [], "page": {"next": None}}
        session = Mock()
        session.get.side_effect = [first_resp, second_resp]
        session.headers = {}

        with patch.object(
            type(provider),
            "_ramp_get_access_token",
            return_value="fresh-bearer",
        ) as mock_token:
            data = provider._ramp_get(session, "/developer/v1/transactions")

        self.assertEqual(data, {"data": [], "page": {"next": None}})
        # Cache cleared then refilled (one refresh call after the 401)
        mock_token.assert_called_once()
        self.assertEqual(session.headers["Authorization"], "Bearer fresh-bearer")
        self.assertEqual(session.get.call_count, 2)

    def test_get_non_2xx_raises(self):
        provider = self._new_provider()
        resp = Mock(ok=False, status_code=500, text="Internal Server Error")
        session = Mock()
        session.get.return_value = resp
        with self.assertRaises(UserError) as ctx:
            provider._ramp_get(session, "/developer/v1/transactions")
        self.assertIn("500", str(ctx.exception))

    def test_get_network_error_raises(self):
        import requests as req_lib

        provider = self._new_provider()
        session = Mock()
        session.get.side_effect = req_lib.RequestException("connection timeout")
        with self.assertRaises(UserError) as ctx:
            provider._ramp_get(session, "/developer/v1/transactions")
        self.assertIn("connection timeout", str(ctx.exception))

    # ------------------------------------------------------------------
    # Base URL
    # ------------------------------------------------------------------

    def test_base_url_sandbox(self):
        provider = self._new_provider(ramp_host="sandbox")
        self.assertEqual(provider._ramp_base_url(), "https://demo-api.ramp.com")

    def test_base_url_production(self):
        provider = self._new_provider(ramp_host="production")
        self.assertEqual(provider._ramp_base_url(), "https://api.ramp.com")

    # ------------------------------------------------------------------
    # Session
    # ------------------------------------------------------------------

    def test_session_uses_bearer_header(self):
        mock_session = MagicMock()
        _SESSION_CLS = (
            "odoo.addons.account_statement_import_online_ramp"
            ".models.online_bank_statement_provider_ramp.requests.Session"
        )
        with patch(_SESSION_CLS, return_value=mock_session):
            self.provider._ramp_session()
        called_headers = mock_session.headers.update.call_args[0][0]
        self.assertEqual(called_headers["Authorization"], "Bearer preset-bearer")
        self.assertEqual(called_headers["Accept"], "application/json")
        # Retry adapter mounted on https:// — confirms transient 5xx will retry.
        mount_calls = mock_session.mount.call_args_list
        self.assertTrue(
            any(call.args[0] == "https://" for call in mount_calls),
            "expected session.mount('https://', ...) to install retry adapter",
        )

    # ------------------------------------------------------------------
    # Safe-URL guard (SSRF / token-leak defense)
    # ------------------------------------------------------------------

    def test_assert_safe_url_accepts_matching_host(self):
        """Sandbox provider accepts demo-api.ramp.com cursor URLs."""
        provider = self._new_provider(ramp_host="sandbox")
        # No raise = pass.
        provider._ramp_assert_safe_url(
            "https://demo-api.ramp.com/developer/v1/transactions?start=abc"
        )

    def test_assert_safe_url_rejects_foreign_host(self):
        """Cursor URL pointing at another host is rejected."""
        provider = self._new_provider(ramp_host="sandbox")
        with self.assertRaises(UserError) as ctx:
            provider._ramp_assert_safe_url("https://attacker.example/steal")
        self.assertIn("unexpected host", str(ctx.exception))

    def test_assert_safe_url_rejects_http(self):
        """Plain HTTP is rejected — no bearer over cleartext, even to Ramp's host."""
        provider = self._new_provider(ramp_host="sandbox")
        with self.assertRaises(UserError):
            provider._ramp_assert_safe_url(
                "http://demo-api.ramp.com/developer/v1/transactions"
            )

    def test_assert_safe_url_rejects_cross_env(self):
        """Sandbox provider rejects a production-host cursor URL and vice versa."""
        sandbox = self._new_provider(ramp_host="sandbox")
        with self.assertRaises(UserError):
            sandbox._ramp_assert_safe_url(
                "https://api.ramp.com/developer/v1/transactions"
            )
        prod = self._new_provider(ramp_host="production")
        with self.assertRaises(UserError):
            prod._ramp_assert_safe_url(
                "https://demo-api.ramp.com/developer/v1/transactions"
            )

    def test_assert_safe_url_accepts_explicit_port(self):
        """``https://demo-api.ramp.com:443/...`` is the same host — accept it."""
        provider = self._new_provider(ramp_host="sandbox")
        provider._ramp_assert_safe_url(
            "https://demo-api.ramp.com:443/developer/v1/transactions?start=abc"
        )

    def test_assert_safe_url_accepts_mixed_case_host(self):
        """Hostnames are case-insensitive per RFC 3986."""
        provider = self._new_provider(ramp_host="sandbox")
        provider._ramp_assert_safe_url(
            "https://Demo-Api.Ramp.Com/developer/v1/transactions?start=abc"
        )

    def test_assert_safe_url_rejects_user_authority_bypass(self):
        """``https://demo-api.ramp.com@evil.com/...`` resolves to evil.com."""
        provider = self._new_provider(ramp_host="sandbox")
        with self.assertRaises(UserError):
            provider._ramp_assert_safe_url(
                "https://demo-api.ramp.com@evil.com/developer/v1/transactions"
            )

    def test_get_rejects_hijacked_next_url(self):
        """A cursor URL pointing at a non-Ramp host fails before the GET."""
        provider = self._new_provider(ramp_host="sandbox")
        session = Mock()
        with self.assertRaises(UserError):
            provider._ramp_get(
                session, "https://attacker.example/transactions?start=abc"
            )
        # Crucially, session.get must NOT have been called — the bearer
        # never leaves the process.
        session.get.assert_not_called()

    # ------------------------------------------------------------------
    # Token-response edge cases
    # ------------------------------------------------------------------

    def test_fetch_token_uses_default_expiry_when_missing(self):
        """A response without ``expires_in`` falls back to a 2h default."""
        provider = self._new_provider(ramp_access_token=False, ramp_token_expiry=False)
        mock_resp = Mock(ok=True, status_code=200)
        mock_resp.json.return_value = {"access_token": "minimal-bearer"}
        mock_session = self._mock_session_with_response(mock_resp)
        _SESSION = (
            "odoo.addons.account_statement_import_online_ramp"
            ".models.online_bank_statement_provider_ramp.requests.Session"
        )
        with patch(_SESSION, return_value=mock_session):
            token = provider._ramp_fetch_access_token()
        self.assertEqual(token, "minimal-bearer")
        # 2h default = 7200s. Expiry should be between now+1h and now+3h.
        now = _utcnow()
        self.assertGreater(provider.ramp_token_expiry, now + timedelta(hours=1))
        self.assertLess(provider.ramp_token_expiry, now + timedelta(hours=3))

    def test_fetch_token_handles_null_expires_in(self):
        """A response with ``expires_in: null`` must not crash on int(None)."""
        provider = self._new_provider(ramp_access_token=False, ramp_token_expiry=False)
        mock_resp = Mock(ok=True, status_code=200)
        mock_resp.json.return_value = {
            "access_token": "null-expiry-bearer",
            "expires_in": None,
        }
        mock_session = self._mock_session_with_response(mock_resp)
        _SESSION = (
            "odoo.addons.account_statement_import_online_ramp"
            ".models.online_bank_statement_provider_ramp.requests.Session"
        )
        with patch(_SESSION, return_value=mock_session):
            token = provider._ramp_fetch_access_token()
        self.assertEqual(token, "null-expiry-bearer")

    def test_fetch_token_missing_access_token_raises(self):
        """A response without ``access_token`` is a clear UserError."""
        provider = self._new_provider(ramp_access_token=False, ramp_token_expiry=False)
        mock_resp = Mock(ok=True, status_code=200)
        mock_resp.json.return_value = {"expires_in": 7200}  # no access_token
        mock_session = self._mock_session_with_response(mock_resp)
        _SESSION = (
            "odoo.addons.account_statement_import_online_ramp"
            ".models.online_bank_statement_provider_ramp.requests.Session"
        )
        with patch(_SESSION, return_value=mock_session):
            with self.assertRaises(UserError) as ctx:
                provider._ramp_fetch_access_token()
        self.assertIn("access_token", str(ctx.exception))

    # ------------------------------------------------------------------
    # Pagination safeguards
    # ------------------------------------------------------------------

    def test_pagination_max_pages_raises(self):
        """A cursor that never terminates is bounded by _MAX_PAGES."""
        from ..models import online_bank_statement_provider_ramp as _mod

        # Always return "there's more" so the loop would run forever
        # without the safeguard.
        infinite_page = {
            "data": [
                {
                    "id": "txn-loop",
                    "amount": 1.0,
                    "state": "CLEARED",
                    "user_transaction_time": "2026-03-01T00:00:00.000Z",
                }
            ],
            "page": {
                "next": "https://demo-api.ramp.com/developer/v1/transactions?start=x"
            },
        }
        # Temporarily lower the cap so the test runs fast.
        original = _mod._MAX_PAGES
        _mod._MAX_PAGES = 5
        try:
            with patch.object(
                type(self.provider), "_ramp_get", return_value=infinite_page
            ):
                with self.assertRaises(UserError) as ctx:
                    self.provider._ramp_fetch_transactions(
                        datetime(2026, 3, 1), datetime(2026, 3, 31)
                    )
        finally:
            _mod._MAX_PAGES = original
        self.assertIn("did not terminate", str(ctx.exception))
