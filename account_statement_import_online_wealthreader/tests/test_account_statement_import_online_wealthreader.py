# Copyright 2025 Wealthreader
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import MagicMock, patch

import requests

from odoo.exceptions import UserError
from odoo.tests import common
from odoo.tools import mute_logger

_provider_module = (
    "odoo.addons.account_statement_import_online_wealthreader"
    ".models.online_bank_statement_provider_wealthreader"
)

MOCK_ENTITIES_RESPONSE = {
    "success": True,
    "payload": [
        {
            "accounts": [
                {
                    "uuid": "acc-uuid-001",
                    "code": "ES12 3456 7890 1234 5678 9012",
                    "name": "Current Account",
                    "currency": "EUR",
                    "subtype": "checking",
                    "balances": {
                        "available": 5000.00,
                        "current": 5200.50,
                    },
                    "transactions": [
                        {
                            "uuid": "tr-uuid-001",
                            "operation_date": "2024-01-15",
                            "value_date": "2024-01-15",
                            "amount": -150.00,
                            "balance": 5200.50,
                            "description": "Electricity bill payment",
                            "categorization": {"type": "utilities"},
                            "transfer_details": {
                                "concept": "Electricity Jan 2024",
                                "sender_receiver": "Electric Corp",
                                "account_number": "ES98 7654 3210 9876 5432 1098",
                            },
                        },
                        {
                            "uuid": "tr-uuid-002",
                            "operation_date": "2024-01-14",
                            "value_date": "2024-01-14",
                            "amount": 2500.00,
                            "balance": 5350.50,
                            "description": "Salary deposit",
                            "categorization": {"type": "income"},
                            "transfer_details": {
                                "concept": "January Salary",
                                "sender_receiver": "Employer Inc.",
                                "account_number": "ES11 2233 4455 6677 8899 0011",
                            },
                        },
                        {
                            "uuid": "tr-uuid-003",
                            "operation_date": "2024-01-10",
                            "value_date": "2024-01-12",
                            "amount": -45.99,
                            "balance": 2850.50,
                            "description": "Online purchase",
                            "transfer_details": {
                                "concept": "Order #12345",
                                "sender_receiver": "Online Shop SL",
                            },
                        },
                    ],
                }
            ],
        }
    ],
    "statistics": {
        "SESSION": "test-session-123",
        "execution_time": 3.5,
        "token": "tok_abc123",
    },
}

MOCK_EMPTY_RESPONSE = {
    "success": True,
    "payload": [{"accounts": []}],
    "statistics": {"SESSION": "test-session-456", "execution_time": 1.0},
}

MOCK_MULTI_ACCOUNT_RESPONSE = {
    "success": True,
    "payload": [
        {
            "accounts": [
                {
                    "uuid": "acc-uuid-001",
                    "code": "ES12 3456 7890 1234 5678 9012",
                    "name": "Current Account",
                    "currency": "EUR",
                    "balances": {"current": 5000.00},
                    "transactions": [],
                },
                {
                    "uuid": "acc-uuid-002",
                    "code": "ES99 8888 7777 6666 5555 4444",
                    "name": "Savings Account",
                    "currency": "EUR",
                    "balances": {"current": 15000.00},
                    "transactions": [],
                },
            ],
        }
    ],
    "statistics": {"SESSION": "test-session-789", "execution_time": 2.0},
}

MOCK_ERROR_RESPONSE = {
    "success": False,
    "error": {"code": 2001, "message": "Invalid credentials"},
    "statistics": {"SESSION": "test-session-err"},
}


class TestAccountStatementImportOnlineWealthreader(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "ES12 3456 7890 1234 5678 9012",
                "partner_id": cls.env.company.partner_id.id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Wealthreader Test Bank",
                "type": "bank",
                "code": "WRTS",
                "currency_id": cls.currency_eur.id,
                "bank_account_id": cls.bank_account.id,
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "journal_id": cls.journal.id,
                "service": "wealthreader",
                "password": "test_api_key",
                "username": "testuser",
                "wealthreader_bank_password": "testpass",
                "wealthreader_entity_code": "testbank",
                "wealthreader_date_field": "value_date",
            }
        )

    def _mock_request(self, response_data):
        """Create a mock for requests.post that returns the given data."""

        class MockResponse:
            status_code = 200
            text = ""

            def json(self):
                return response_data

        return patch(
            f"{_provider_module}.requests.post",
            return_value=MockResponse(),
        )

    # ------------------------------------------------------------------
    # A) _get_available_services
    # ------------------------------------------------------------------

    def test_get_available_services(self):
        """Wealthreader must be among available services."""
        services = self.provider._get_available_services()
        service_keys = [s[0] for s in services]
        self.assertIn("wealthreader", service_keys)

    # ------------------------------------------------------------------
    # B) _obtain_statement_data — delegation
    # ------------------------------------------------------------------

    def test_obtain_statement_data(self):
        """Standard transaction import with 3 lines."""
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        with self._mock_request(MOCK_ENTITIES_RESPONSE):
            lines, statement = self.provider._obtain_statement_data(
                date_since, date_until
            )
        self.assertEqual(len(lines), 3)
        self.assertEqual(statement.get("balance_end_real"), 5200.50)
        self.assertEqual(self.provider.wealthreader_token, "tok_abc123")
        self.assertEqual(self.provider.wealthreader_account_uuid, "acc-uuid-001")

    def test_obtain_statement_data_delegates_for_other_service(self):
        """When service is not wealthreader, delegates to super."""
        # Create a provider with a different service to confirm delegation
        journal2 = self.env["account.journal"].create(
            {
                "name": "Dummy Test Bank",
                "type": "bank",
                "code": "DMTS",
                "currency_id": self.currency_eur.id,
            }
        )
        dummy_provider = self.env["online.bank.statement.provider"].create(
            {
                "journal_id": journal2.id,
                "service": "dummy",
            }
        )
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        result = dummy_provider._obtain_statement_data(date_since, date_until)
        # The base/dummy service returns an empty list
        self.assertEqual(result, [])

    # ------------------------------------------------------------------
    # C) _wealthreader_obtain_statement_data
    # ------------------------------------------------------------------

    def test_obtain_no_accounts(self):
        """Payload without accounts returns empty data."""
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        with self._mock_request(MOCK_EMPTY_RESPONSE):
            lines, statement = self.provider._obtain_statement_data(
                date_since, date_until
            )
        self.assertEqual(lines, [])
        self.assertEqual(statement, {})

    def test_obtain_persists_account_uuid_and_code(self):
        """Account UUID and code are persisted after first sync."""
        self.assertFalse(self.provider.wealthreader_account_uuid)
        self.assertFalse(self.provider.wealthreader_account_code)
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        with self._mock_request(MOCK_ENTITIES_RESPONSE):
            self.provider._obtain_statement_data(date_since, date_until)
        self.assertEqual(self.provider.wealthreader_account_uuid, "acc-uuid-001")
        self.assertEqual(
            self.provider.wealthreader_account_code, "ES12 3456 7890 1234 5678 9012"
        )

    def test_obtain_no_balance_current(self):
        """When balances has no 'current' key, statement_values has no balance."""
        response = {
            "success": True,
            "payload": [
                {
                    "accounts": [
                        {
                            "uuid": "acc-1",
                            "code": "ES12 3456 7890 1234 5678 9012",
                            "name": "Test",
                            "balances": {},
                            "transactions": [],
                        }
                    ]
                }
            ],
            "statistics": {},
        }
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        with self._mock_request(response):
            _, statement = self.provider._obtain_statement_data(date_since, date_until)
        self.assertNotIn("balance_end_real", statement)

    # ------------------------------------------------------------------
    # D) _wealthreader_fetch_entity_data
    # ------------------------------------------------------------------

    def test_missing_api_key_raises(self):
        """Missing API key raises UserError."""
        self.provider.password = False
        with self.assertRaises(UserError):
            self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )

    def test_missing_entity_code_raises(self):
        """Missing entity code raises UserError."""
        self.provider.wealthreader_entity_code = False
        with self.assertRaises(UserError):
            self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )

    def _get_posted_data(self, mock_post):
        """Extract the data dict sent to requests.post.

        Handles both modern mock.call_args (with .kwargs) and older
        tuple-based call_args (args, kwargs).
        """
        if not mock_post.call_args:
            return {}
        call = mock_post.call_args
        if hasattr(call, "kwargs"):
            # Modern unittest.mock (Python 3.8+)
            return call.kwargs.get("data", {})
        else:
            # Older mock: call is a tuple (args_tuple, kwargs_dict)
            if isinstance(call, tuple) and len(call) > 1:
                return call[1].get("data", {})
            return {}

    def test_fetch_uses_token_when_set(self):
        """When token is set, sends token instead of user/password."""
        self.provider.wealthreader_token = "existing_token"
        with self._mock_request(MOCK_ENTITIES_RESPONSE) as mock_post:
            self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
            posted = self._get_posted_data(mock_post)
            self.assertEqual(posted["token"], "existing_token")
            self.assertNotIn("user", posted)

    def test_fetch_uses_username_password_when_no_token(self):
        """Without token, sends user and password from the credential fields."""
        self.provider.wealthreader_token = False
        with self._mock_request(MOCK_ENTITIES_RESPONSE) as mock_post:
            self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
            posted = self._get_posted_data(mock_post)
            self.assertEqual(posted["user"], "testuser")
            self.assertEqual(posted["password"], "testpass")
            self.assertNotIn("token", posted)

    def test_fetch_username_without_bank_password(self):
        """With username but no bank password, sends user without password."""
        self.provider.wealthreader_token = False
        self.provider.wealthreader_bank_password = False
        with self._mock_request(MOCK_ENTITIES_RESPONSE) as mock_post:
            self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
            posted = self._get_posted_data(mock_post)
            self.assertEqual(posted["user"], "testuser")
            self.assertNotIn("password", posted)

    def test_fetch_persists_new_token(self):
        """Token from statistics is persisted when new."""
        self.provider.wealthreader_token = False
        with self._mock_request(MOCK_ENTITIES_RESPONSE):
            self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(self.provider.wealthreader_token, "tok_abc123")

    def test_fetch_does_not_overwrite_same_token(self):
        """Token is not rewritten if it has not changed."""
        self.provider.wealthreader_token = "tok_abc123"
        with self._mock_request(MOCK_ENTITIES_RESPONSE):
            with patch.object(type(self.provider), "write") as mock_write:
                self.provider._wealthreader_fetch_entity_data(
                    datetime(2024, 1, 1), datetime(2024, 1, 31)
                )
                # write should not have been called with token key
                for call in mock_write.call_args_list:
                    self.assertNotIn("wealthreader_token", call[0][0])

    def test_fetch_payload_none(self):
        """Payload that is None returns empty dict."""
        response = {"success": True, "payload": None, "statistics": {}}
        with self._mock_request(response):
            result = self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(result, {})

    def test_fetch_payload_empty_list(self):
        """Payload that is an empty list returns empty dict."""
        response = {"success": True, "payload": [], "statistics": {}}
        with self._mock_request(response):
            result = self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(result, {})

    def test_fetch_payload_list_with_non_dict(self):
        """Payload list whose first element is not a dict returns empty dict."""
        response = {"success": True, "payload": ["not-a-dict"], "statistics": {}}
        with self._mock_request(response):
            result = self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(result, {})

    def test_fetch_payload_list_with_dict(self):
        """Payload list with a dict returns that dict."""
        expected = {"accounts": []}
        response = {"success": True, "payload": [expected], "statistics": {}}
        with self._mock_request(response):
            result = self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(result, expected)

    def test_fetch_payload_dict(self):
        """Payload that is already a dict is returned directly."""
        expected = {"accounts": [{"uuid": "x"}]}
        response = {"success": True, "payload": expected, "statistics": {}}
        with self._mock_request(response):
            result = self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(result, expected)

    def test_fetch_payload_non_dict_non_list(self):
        """Payload that is neither dict nor list returns empty dict."""
        response = {"success": True, "payload": "unexpected", "statistics": {}}
        with self._mock_request(response):
            result = self.provider._wealthreader_fetch_entity_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        self.assertEqual(result, {})

    # ------------------------------------------------------------------
    # E) _wealthreader_select_account
    # ------------------------------------------------------------------

    def test_select_account_by_uuid(self):
        """Match account by stored UUID."""
        self.provider.wealthreader_account_uuid = "acc-uuid-002"
        accounts = MOCK_MULTI_ACCOUNT_RESPONSE["payload"][0]["accounts"]
        result = self.provider._wealthreader_select_account(accounts)
        self.assertEqual(result["uuid"], "acc-uuid-002")

    def test_select_account_by_iban(self):
        """Match account by journal IBAN."""
        self.provider.wealthreader_account_uuid = False
        accounts = MOCK_MULTI_ACCOUNT_RESPONSE["payload"][0]["accounts"]
        result = self.provider._wealthreader_select_account(accounts)
        self.assertEqual(result["uuid"], "acc-uuid-001")

    def test_select_account_single(self):
        """Single account is returned directly without matching."""
        self.provider.wealthreader_account_uuid = False
        accounts = [{"uuid": "only-one", "code": "XX00 0000", "name": "Solo"}]
        # Journal IBAN doesn't match, but only one account => auto-select
        result = self.provider._wealthreader_select_account(accounts)
        self.assertEqual(result["uuid"], "only-one")

    def test_select_account_multi_no_match_raises(self):
        """Multiple accounts without match raises UserError."""
        self.provider.wealthreader_account_uuid = False
        accounts = [
            {"uuid": "a1", "code": "XX11 1111", "name": "Acc A"},
            {"uuid": "a2", "code": "XX22 2222", "name": "Acc B"},
        ]
        with self.assertRaises(UserError) as ctx:
            self.provider._wealthreader_select_account(accounts)
        self.assertIn("Acc A", str(ctx.exception))
        self.assertIn("Acc B", str(ctx.exception))

    # ------------------------------------------------------------------
    # F) _wealthreader_parse_transactions
    # ------------------------------------------------------------------

    def test_parse_transactions_skips_invalid(self):
        """Invalid transactions (amount=None) are filtered out."""
        transactions = [
            {"uuid": "t1", "value_date": "2024-01-01", "amount": 100},
            {"uuid": "t2", "value_date": "2024-01-02", "amount": None},
            {"uuid": "t3", "value_date": "2024-01-03", "amount": 50},
        ]
        lines = self.provider._wealthreader_parse_transactions(transactions)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["unique_import_id"], "WR-t1")
        self.assertEqual(lines[1]["unique_import_id"], "WR-t3")

    # ------------------------------------------------------------------
    # G) _wealthreader_transaction_to_line
    # ------------------------------------------------------------------

    def test_transaction_line_amount_none(self):
        """Transaction with amount=None returns None."""
        result = self.provider._wealthreader_transaction_to_line(
            {"amount": None, "value_date": "2024-01-01"}
        )
        self.assertIsNone(result)

    def test_transaction_line_no_date(self):
        """Transaction without any date returns None."""
        result = self.provider._wealthreader_transaction_to_line({"amount": 10})
        self.assertIsNone(result)

    def test_transaction_line_operation_date(self):
        """date_field=operation_date uses operation_date."""
        self.provider.wealthreader_date_field = "operation_date"
        line = self.provider._wealthreader_transaction_to_line(
            {
                "amount": 10,
                "operation_date": "2024-01-10",
                "value_date": "2024-01-12",
                "uuid": "t1",
            }
        )
        self.assertEqual(line["date"], "2024-01-10")

    def test_transaction_line_value_date(self):
        """date_field=value_date uses value_date."""
        self.provider.wealthreader_date_field = "value_date"
        line = self.provider._wealthreader_transaction_to_line(
            {
                "amount": 10,
                "operation_date": "2024-01-10",
                "value_date": "2024-01-12",
                "uuid": "t1",
            }
        )
        self.assertEqual(line["date"], "2024-01-12")

    def test_transaction_line_partner_info(self):
        """Partner name and account number are included when present."""
        line = self.provider._wealthreader_transaction_to_line(
            {
                "amount": 10,
                "value_date": "2024-01-01",
                "uuid": "t1",
                "transfer_details": {
                    "sender_receiver": "Partner Co",
                    "account_number": "ES00 1234",
                },
            }
        )
        self.assertEqual(line["partner_name"], "Partner Co")
        self.assertEqual(line["account_number"], "ES00 1234")

    def test_transaction_line_no_partner_info(self):
        """Without transfer_details, partner fields are absent."""
        line = self.provider._wealthreader_transaction_to_line(
            {"amount": 10, "value_date": "2024-01-01", "uuid": "t1"}
        )
        self.assertNotIn("partner_name", line)
        self.assertNotIn("account_number", line)

    def test_transaction_line_no_narration(self):
        """Transaction with no detail produces no narration key."""
        line = self.provider._wealthreader_transaction_to_line(
            {"amount": 10, "value_date": "2024-01-01", "uuid": "t1"}
        )
        self.assertNotIn("narration", line)

    def test_transaction_line_with_narration(self):
        """Transaction with description produces narration."""
        line = self.provider._wealthreader_transaction_to_line(
            {
                "amount": 10,
                "value_date": "2024-01-01",
                "uuid": "t1",
                "description": "Some payment",
            }
        )
        self.assertIn("narration", line)
        self.assertIn("Some payment", line["narration"])

    def test_transaction_fields_full(self):
        """Verify full field mapping on a complete transaction."""
        with self._mock_request(MOCK_ENTITIES_RESPONSE):
            lines, _ = self.provider._obtain_statement_data(
                datetime(2024, 1, 1), datetime(2024, 1, 31)
            )
        line = lines[0]
        self.assertEqual(line["amount"], -150.00)
        self.assertEqual(line["payment_ref"], "Electricity Jan 2024")
        self.assertEqual(line["unique_import_id"], "WR-tr-uuid-001")
        self.assertEqual(line["partner_name"], "Electric Corp")
        self.assertEqual(line["account_number"], "ES98 7654 3210 9876 5432 1098")
        self.assertEqual(line["date"], "2024-01-15")

    # ------------------------------------------------------------------
    # G.ref) _wealthreader_get_payment_ref
    # ------------------------------------------------------------------

    def test_payment_ref_from_concept(self):
        """Payment ref comes from transfer concept when available."""
        ref = self.provider._wealthreader_get_payment_ref(
            {"transfer_details": {"concept": "Wire transfer"}, "description": "Desc"}
        )
        self.assertEqual(ref, "Wire transfer")

    def test_payment_ref_falls_back_to_description(self):
        """Payment ref falls back to description when no concept."""
        ref = self.provider._wealthreader_get_payment_ref(
            {"description": "Fallback desc"}
        )
        self.assertEqual(ref, "Fallback desc")

    def test_payment_ref_empty(self):
        """Payment ref is empty string when nothing available."""
        ref = self.provider._wealthreader_get_payment_ref({})
        self.assertEqual(ref, "")

    # ------------------------------------------------------------------
    # G.id) _wealthreader_get_unique_id
    # ------------------------------------------------------------------

    def test_unique_id_with_uuid(self):
        """Unique ID uses UUID when present."""
        uid = self.provider._wealthreader_get_unique_id({"uuid": "abc-123"})
        self.assertEqual(uid, "WR-abc-123")

    def test_unique_id_fallback(self):
        """Unique ID falls back to a stable date+amount+digest when no UUID."""
        uid = self.provider._wealthreader_get_unique_id(
            {"value_date": "2024-01-01", "amount": 100, "description": "test"}
        )
        # sha1("test")[:12] — stable across processes, unlike hash()
        self.assertEqual(uid, "WR-2024-01-01-100-a94a8fe5ccb1")

    # ------------------------------------------------------------------
    # H) _wealthreader_build_note
    # ------------------------------------------------------------------

    def test_build_note_full(self):
        """Note with all fields present and different dates."""
        note = self.provider._wealthreader_build_note(
            {
                "description": "Payment",
                "operation_date": "2024-01-10",
                "value_date": "2024-01-12",
                "categorization": {"type": "transfer"},
                "transfer_details": {
                    "concept": "Wire",
                    "sender_receiver": "John",
                    "account_number": "ES00 1234",
                },
            }
        )
        self.assertIn("Payment", note)
        self.assertIn("Wire", note)
        self.assertIn("John", note)
        self.assertIn("ES00 1234", note)
        self.assertIn("transfer", note)
        self.assertIn("2024-01-10", note)
        self.assertIn("2024-01-12", note)

    def test_build_note_concept_equals_description(self):
        """Concept is not duplicated when it matches description."""
        note = self.provider._wealthreader_build_note(
            {
                "description": "Same text",
                "transfer_details": {"concept": "Same text"},
            }
        )
        # "Same text" appears once as description, concept line is skipped
        self.assertEqual(note.count("Same text"), 1)

    def test_build_note_empty(self):
        """Transaction with no details returns empty note."""
        note = self.provider._wealthreader_build_note({})
        self.assertEqual(note, "")

    def test_build_note_same_dates(self):
        """When operation_date == value_date, date line is not added."""
        note = self.provider._wealthreader_build_note(
            {
                "description": "Test",
                "operation_date": "2024-01-15",
                "value_date": "2024-01-15",
            }
        )
        self.assertNotIn("Operation date", note)

    # ------------------------------------------------------------------
    # I) _wealthreader_request
    # ------------------------------------------------------------------

    def test_request_timeout(self):
        """Timeout raises UserError."""
        with patch(
            f"{_provider_module}.requests.post",
            side_effect=requests.exceptions.Timeout("timed out"),
        ):
            with self.assertRaises(UserError) as ctx:
                self.provider._wealthreader_request("/entities/", {"code": "x"})
            self.assertIn("timed out", str(ctx.exception).lower())

    def test_request_connection_error(self):
        """ConnectionError raises UserError."""
        with patch(
            f"{_provider_module}.requests.post",
            side_effect=requests.exceptions.ConnectionError("refused"),
        ):
            with self.assertRaises(UserError) as ctx:
                self.provider._wealthreader_request("/entities/", {"code": "x"})
            self.assertIn("connect", str(ctx.exception).lower())

    @mute_logger(_provider_module)
    def test_request_invalid_json(self):
        """Non-JSON response raises UserError."""
        mock_resp = MagicMock()
        mock_resp.json.side_effect = ValueError("No JSON")
        mock_resp.status_code = 502
        mock_resp.text = "Bad Gateway"
        with patch(f"{_provider_module}.requests.post", return_value=mock_resp):
            with self.assertRaises(UserError) as ctx:
                self.provider._wealthreader_request("/entities/", {"code": "x"})
            self.assertIn("502", str(ctx.exception))

    @mute_logger(_provider_module)
    def test_request_api_error(self):
        """API error with success=False raises UserError."""
        with self._mock_request(MOCK_ERROR_RESPONSE):
            with self.assertRaises(UserError) as ctx:
                self.provider._wealthreader_request("/entities/", {"code": "x"})
            self.assertIn("2001", str(ctx.exception))
            self.assertIn("Invalid credentials", str(ctx.exception))

    def test_request_success(self):
        """Successful request returns result dict."""
        expected = {"success": True, "payload": [], "statistics": {}}
        with self._mock_request(expected):
            result = self.provider._wealthreader_request("/entities/", {"code": "x"})
        self.assertEqual(result, expected)

    # ------------------------------------------------------------------
    # J) action_wealthreader_test_connection
    # ------------------------------------------------------------------

    def test_test_connection_with_accounts(self):
        """Test connection with accounts returns notification."""
        with self._mock_request(MOCK_ENTITIES_RESPONSE):
            result = self.provider.action_wealthreader_test_connection()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertEqual(result["tag"], "display_notification")
        self.assertIn("1 account", result["params"]["message"])
        self.assertIn("Current Account", result["params"]["message"])

    def test_test_connection_no_accounts(self):
        """Test connection without accounts returns alternative message."""
        with self._mock_request(MOCK_EMPTY_RESPONSE):
            result = self.provider.action_wealthreader_test_connection()
        self.assertEqual(result["type"], "ir.actions.client")
        self.assertIn("no accounts", result["params"]["message"].lower())

    def test_test_connection_error_propagates(self):
        """UserError from fetch is wrapped and re-raised."""
        self.provider.password = False
        with self.assertRaises(UserError) as ctx:
            self.provider.action_wealthreader_test_connection()
        self.assertIn("Connection test failed", str(ctx.exception))

    # ------------------------------------------------------------------
    # Integration: multi-account IBAN match via full flow
    # ------------------------------------------------------------------

    def test_multi_account_iban_match(self):
        """With multiple accounts, match by IBAN."""
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        with self._mock_request(MOCK_MULTI_ACCOUNT_RESPONSE):
            self.provider._obtain_statement_data(date_since, date_until)
        self.assertEqual(self.provider.wealthreader_account_uuid, "acc-uuid-001")

    def test_multi_account_no_match_raises(self):
        """Multiple accounts without IBAN match raises UserError."""
        other_bank_account = self.env["res.partner.bank"].create(
            {
                "acc_number": "XX00 0000 0000 0000 0000 0000",
                "partner_id": self.env.company.partner_id.id,
            }
        )
        other_journal = self.env["account.journal"].create(
            {
                "name": "Wealthreader No Match",
                "type": "bank",
                "code": "WRNM",
                "currency_id": self.currency_eur.id,
                "bank_account_id": other_bank_account.id,
            }
        )
        other_provider = self.env["online.bank.statement.provider"].create(
            {
                "journal_id": other_journal.id,
                "service": "wealthreader",
                "password": "test_api_key",
                "wealthreader_entity_code": "testbank",
            }
        )
        date_since = datetime(2024, 1, 1)
        date_until = datetime(2024, 1, 31)
        with self._mock_request(MOCK_MULTI_ACCOUNT_RESPONSE):
            with self.assertRaises(UserError):
                other_provider._obtain_statement_data(date_since, date_until)
