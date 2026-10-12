# Copyright 2024 Ledo Enterprises
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase

SAMPLE_ACCOUNTS = {
    "accounts": [
        {"id": "acct-uuid-001", "name": "Mercury Checking"},
    ]
}

SAMPLE_TRANSACTIONS = {
    "transactions": [
        {
            "id": "txn-uuid-001",
            "amount": -150.00,
            "status": "sent",
            "bankDescription": "ACH PAYMENT VENDOR CO",
            "externalMemo": "Invoice 1234",
            "note": "",
            "counterpartyName": "Vendor Co",
            "counterpartyAccountNumber": "123456789",
            "createdAt": "2024-03-01T12:00:00.000Z",
            "postedAt": "2024-03-02T08:00:00.000Z",
        },
        {
            "id": "txn-uuid-002",
            "amount": 5000.00,
            "status": "sent",
            "bankDescription": "WIRE TRANSFER IN",
            "externalMemo": "",
            "note": "Client payment",
            "counterpartyName": "Client LLC",
            "counterpartyAccountNumber": None,
            "createdAt": "2024-03-05T10:00:00.000Z",
            "postedAt": "2024-03-05T10:00:00.000Z",
        },
    ],
    "page": {"nextPage": None, "previousPage": None},
}

# Two-page dataset for pagination tests
PAGE_1 = {
    "transactions": [
        {
            "id": f"txn-page1-{i:03d}",
            "amount": float(i),
            "status": "sent",
            "bankDescription": f"TXN {i}",
            "externalMemo": "",
            "note": "",
            "counterpartyName": None,
            "counterpartyAccountNumber": None,
            "createdAt": "2024-03-01T00:00:00.000Z",
            "postedAt": "2024-03-01T00:00:00.000Z",
        }
        for i in range(500)
    ],
    "page": {"nextPage": "cursor-abc", "previousPage": None},
}

PAGE_2 = {
    "transactions": [
        {
            "id": "txn-page2-001",
            "amount": 99.0,
            "status": "sent",
            "bankDescription": "LAST TXN",
            "externalMemo": "",
            "note": "",
            "counterpartyName": None,
            "counterpartyAccountNumber": None,
            "createdAt": "2024-03-15T00:00:00.000Z",
            "postedAt": "2024-03-15T00:00:00.000Z",
        }
    ],
    "page": {"nextPage": None, "previousPage": "cursor-abc"},
}

_journal_seq = [0]


class TestMercuryProvider(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Always create a dedicated journal — the unique constraint on
        # online_bank_statement_provider(journal_id) forbids sharing one.
        cls.journal = cls.env["account.journal"].create(
            {"name": "Mercury Test Bank", "type": "bank", "code": "MRCTEST"}
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "journal_id": cls.journal.id,
                "service": "mercury",
                "password": "test-api-key",
                "mercury_account_id": "acct-uuid-001",
                "mercury_include_pending": False,
            }
        )

    def _new_provider(self, **vals):
        """Create a provider with a fresh journal.

        Avoids the journal_id unique constraint.
        """
        _journal_seq[0] += 1
        journal = self.env["account.journal"].create(
            {
                "name": f"Mercury Test {_journal_seq[0]}",
                "type": "bank",
                "code": f"MRC{_journal_seq[0]:02d}",
            }
        )
        base = {
            "journal_id": journal.id,
            "service": "mercury",
            "password": "test-api-key",
            "mercury_account_id": "acct-uuid-001",
            "mercury_include_pending": False,
        }
        base.update(vals)
        return self.env["online.bank.statement.provider"].create(base)

    @staticmethod
    def _mock_get(session, path, params=None):
        """Side-effect for _mercury_get: dispatches by path.

        Note: patch.object on the class replaces the method with a Mock that is
        NOT bound, so side_effects receive (session, path, params) — not self.
        """
        if path == "/accounts":
            return SAMPLE_ACCOUNTS
        if path.endswith("/transactions"):
            return SAMPLE_TRANSACTIONS
        return {}

    # ------------------------------------------------------------------
    # Service registration
    # ------------------------------------------------------------------

    def test_service_registered(self):
        services = dict(self.provider._get_available_services())
        self.assertIn("mercury", services)

    # ------------------------------------------------------------------
    # Core data fetch
    # ------------------------------------------------------------------

    def test_obtain_statement_data(self):
        date_since = datetime(2024, 3, 1)
        date_until = datetime(2024, 3, 31)
        with patch.object(
            type(self.provider), "_mercury_get", side_effect=self._mock_get
        ):
            lines, meta = self.provider._obtain_statement_data(date_since, date_until)
        self.assertEqual(len(lines), 2)
        self.assertEqual(meta, {})

    def test_obtain_statement_data_delegates_non_mercury(self):
        """Provider with a different service falls through to super()."""
        date_since = datetime(2024, 3, 1)
        date_until = datetime(2024, 3, 31)
        dummy = self._new_provider(service="dummy")
        result = dummy._obtain_statement_data(date_since, date_until)
        # Base returns empty list (no lines), not a tuple — just confirm no crash
        self.assertIsNotNone(result)

    # ------------------------------------------------------------------
    # Pagination
    # ------------------------------------------------------------------

    def test_pagination_fetches_all_pages(self):
        """Two-page response yields transactions from both pages."""
        call_count = [0]

        def _paged_get(session, path, params=None):
            if not path.endswith("/transactions"):
                return SAMPLE_ACCOUNTS
            call_count[0] += 1
            if call_count[0] == 1:
                return PAGE_1
            return PAGE_2

        with patch.object(type(self.provider), "_mercury_get", side_effect=_paged_get):
            txns = self.provider._mercury_fetch_transactions(
                datetime(2024, 3, 1), datetime(2024, 3, 31)
            )

        self.assertEqual(len(txns), 501)  # 500 + 1
        self.assertEqual(call_count[0], 2)

    def test_pagination_preserves_filter_params(self):
        """Date and status params are kept on subsequent pages (not dropped)."""
        captured_params = []

        def _capture_get(session, path, params=None):
            if path.endswith("/transactions"):
                captured_params.append(dict(params or {}))
                # Return full page 1 first, then empty page 2
                if len(captured_params) == 1:
                    return PAGE_1
            return PAGE_2

        with patch.object(
            type(self.provider), "_mercury_get", side_effect=_capture_get
        ):
            self.provider._mercury_fetch_transactions(
                datetime(2024, 3, 1), datetime(2024, 3, 31)
            )

        self.assertGreaterEqual(len(captured_params), 2)
        # Both pages must carry start/end date filters
        for p in captured_params:
            self.assertIn("start", p)
            self.assertIn("end", p)
        # Second page must include the cursor offset
        self.assertEqual(captured_params[1].get("offset"), "cursor-abc")

    # ------------------------------------------------------------------
    # Transaction mapping
    # ------------------------------------------------------------------

    def test_transaction_mapping(self):
        txn = SAMPLE_TRANSACTIONS["transactions"][0]
        line = self.provider._mercury_transaction_to_line(txn)

        self.assertEqual(line["unique_import_id"], "txn-uuid-001")
        self.assertAlmostEqual(line["amount"], -150.00)
        self.assertEqual(line["partner_name"], "Vendor Co")
        self.assertEqual(line["account_number"], "123456789")
        self.assertIn("ACH PAYMENT", line["ref"])
        self.assertIsInstance(line["date"], datetime)

    def test_transaction_mapping_no_counterparty(self):
        txn = SAMPLE_TRANSACTIONS["transactions"][1]
        line = self.provider._mercury_transaction_to_line(txn)

        self.assertEqual(line["unique_import_id"], "txn-uuid-002")
        self.assertAlmostEqual(line["amount"], 5000.00)
        self.assertNotIn("account_number", line)
        self.assertIn("Client payment", line["ref"])

    def test_transaction_ref_fallback_to_slash(self):
        """Transaction with no description fields gets ref='/'."""
        txn = {
            "id": "txn-empty",
            "amount": 1.0,
            "bankDescription": None,
            "externalMemo": None,
            "note": None,
            "counterpartyName": None,
            "counterpartyAccountNumber": None,
            "createdAt": "2024-03-01T00:00:00.000Z",
            "postedAt": None,
        }
        line = self.provider._mercury_transaction_to_line(txn)
        self.assertEqual(line["ref"], "/")

    # ------------------------------------------------------------------
    # Datetime parsing
    # ------------------------------------------------------------------

    def test_parse_datetime_z_suffix(self):
        dt = self.provider._mercury_parse_datetime("2024-03-15T14:30:00.000Z")
        self.assertIsInstance(dt, datetime)
        self.assertIsNone(dt.tzinfo)

    def test_parse_datetime_offset(self):
        dt = self.provider._mercury_parse_datetime("2024-03-15T14:30:00+00:00")
        self.assertIsInstance(dt, datetime)
        self.assertIsNone(dt.tzinfo)

    def test_parse_datetime_none(self):
        dt = self.provider._mercury_parse_datetime(None)
        self.assertIsInstance(dt, datetime)

    def test_parse_datetime_malformed_falls_back_to_now(self):
        dt = self.provider._mercury_parse_datetime("not-a-date")
        self.assertIsInstance(dt, datetime)

    # ------------------------------------------------------------------
    # API session / authentication
    # ------------------------------------------------------------------

    def test_missing_api_key_raises(self):
        provider_no_key = self._new_provider(password=False)
        with self.assertRaises(UserError):
            provider_no_key._mercury_session()

    def test_secret_token_prefix_normalised(self):
        """Bare token is prefixed; already-prefixed token is not double-prefixed."""
        mock_session = MagicMock()
        _SESSION = (
            "odoo.addons.account_statement_import_online_mercury"
            ".models.online_bank_statement_provider_mercury.requests.Session"
        )
        with patch(_SESSION, return_value=mock_session):
            self._new_provider(password="mytoken")._mercury_session()
            bare_auth = mock_session.headers.update.call_args[0][0]["Authorization"]

            mock_session.reset_mock()
            self._new_provider(password="secret-token:mytoken")._mercury_session()
            prefixed_auth = mock_session.headers.update.call_args[0][0]["Authorization"]

        self.assertEqual(bare_auth, "Bearer secret-token:mytoken")
        self.assertEqual(bare_auth, prefixed_auth)

    # ------------------------------------------------------------------
    # API error handling
    # ------------------------------------------------------------------

    def test_http_401_raises_user_error(self):
        """Invalid API key (HTTP 401) raises a clear UserError."""
        resp = Mock(ok=False, status_code=401, text="Unauthorized")
        session = Mock()
        session.get.return_value = resp

        with self.assertRaises(UserError) as ctx:
            self.provider._mercury_get(session, "/accounts")
        self.assertIn("401", str(ctx.exception))

    def test_http_error_raises_user_error(self):
        """Any non-2xx response raises UserError with status and body."""
        resp = Mock(ok=False, status_code=429, text="Rate limit exceeded")
        session = Mock()
        session.get.return_value = resp

        with self.assertRaises(UserError) as ctx:
            self.provider._mercury_get(session, "/accounts")
        self.assertIn("429", str(ctx.exception))

    def test_request_exception_raises_user_error(self):
        """Network-level failure (timeout, DNS) raises UserError."""
        import requests as req_lib

        session = Mock()
        session.get.side_effect = req_lib.RequestException("connection timeout")

        with self.assertRaises(UserError) as ctx:
            self.provider._mercury_get(session, "/accounts")
        self.assertIn("connection timeout", str(ctx.exception))

    # ------------------------------------------------------------------
    # Account resolution
    # ------------------------------------------------------------------

    def test_auto_detect_account(self):
        """When mercury_account_id is blank, first account from /accounts is used."""
        provider = self._new_provider(mercury_account_id=False, password="test-key")
        with patch.object(type(provider), "_mercury_get", side_effect=self._mock_get):
            account_id = provider._mercury_resolve_account_id(MagicMock())
        self.assertEqual(account_id, "acct-uuid-001")

    def test_no_accounts_raises_user_error(self):
        """Empty accounts list raises UserError."""

        def _no_accounts(session, path, params=None):
            return {"accounts": []}

        provider = self._new_provider(mercury_account_id=False, password="test-key")
        with patch.object(type(provider), "_mercury_get", side_effect=_no_accounts):
            with self.assertRaises(UserError):
                provider._mercury_resolve_account_id(MagicMock())

    def test_explicit_account_id_skips_api_call(self):
        """When mercury_account_id is set, /accounts is never called."""
        mock_get = MagicMock()
        with patch.object(type(self.provider), "_mercury_get", mock_get):
            account_id = self.provider._mercury_resolve_account_id(MagicMock())
        mock_get.assert_not_called()
        self.assertEqual(account_id, "acct-uuid-001")
