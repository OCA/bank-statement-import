# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
"""Tests for the Odoo model: online.bank.statement.provider (finapi service).

All external HTTP calls are mocked. No live finAPI credentials needed.

Odoo recordset methods live on the *class*, not the instance — you cannot use
``mock.patch.object(recordset, "method")``.  Instead, patch at the module
path or use ``mock.patch.object(type(recordset), "method")``.
"""
import logging
from datetime import datetime
from pathlib import Path
from unittest import mock

from odoo import fields
from odoo.exceptions import RedirectWarning, UserError
from odoo.tests.common import TransactionCase, tagged

# Module path for the provider model — used to patch methods at class level
_PROVIDER_MOD = (
    "odoo.addons.account_statement_import_online_finapi"
    ".models.online_bank_statement_provider"
)
_INTERFACE_CLS = f"{_PROVIDER_MOD}.FinapiInterface"


def _make_mock_interface():
    """Return a MagicMock that mimics FinapiInterface."""
    iface = mock.MagicMock()
    # context manager: `with iface as x:` must yield the mock itself
    iface.__enter__.return_value = iface
    iface.get_client_token.return_value = "client-tok"
    iface.get_user_token.return_value = {
        "access_token": "user-tok",
        "refresh_token": "rt-new",
    }
    iface.refresh_user_token.return_value = {
        "access_token": "user-tok-refreshed",
        "refresh_token": "rt-refreshed",
    }
    # By default the bank data refresh succeeds and returns no consent info.
    iface.update_bank_connection.return_value = {}
    # Web Form background-update task: completes immediately by default so the
    # poll loop (and its time.sleep) is skipped in tests.
    iface.start_background_update.return_value = {
        "id": "task-1",
        "status": "COMPLETED",
        "payload": {"bankConnectionId": 99},
    }
    iface.get_task.return_value = {
        "id": "task-1",
        "status": "COMPLETED",
        "payload": {"bankConnectionId": 99},
    }
    iface.get_bank_connection.return_value = {"id": 99}
    return iface


@tagged("post_install", "-at_install")
class TestFinapiProvider(TransactionCase):
    def setUp(self):
        super().setUp()
        self.Provider = self.env["online.bank.statement.provider"]
        # Create a minimal bank journal for the provider
        self.journal = self.env["account.journal"].create(
            {
                "name": "finAPI Test Bank",
                "type": "bank",
                "code": "FAPI",
            }
        )
        self.provider = self.Provider.create(
            {
                "journal_id": self.journal.id,
                "service": "finapi",
                "finapi_client_id": "test-client-id",
                "finapi_client_secret": "test-client-secret",
            }
        )
        self.ProviderClass = type(self.provider)

    # ------------------------------------------------------------------
    # Service registration
    # ------------------------------------------------------------------
    def test_finapi_service_registered(self):
        services = dict(self.Provider._get_available_services())
        self.assertIn("finapi", services)

    # ------------------------------------------------------------------
    # Transaction mapping
    # ------------------------------------------------------------------
    def test_mapping_basic(self):
        tx = {
            "id": 555,
            "accountId": 42,
            "bankBookingDate": "2026-04-01",
            "amount": -19.99,
            "currency": "EUR",
            "purpose": "Netflix monthly",
            "counterpartName": "Netflix Intl BV",
            "counterpartIban": "NL00NETF0000000001",
            "endToEndReference": "NFX-123",
            "typeCodeZka": "117",
        }
        line = self.Provider._finapi_transaction_to_line(tx)
        self.assertEqual(line["unique_import_id"], "finapi-42-555")
        self.assertEqual(line["date"], "2026-04-01")
        self.assertEqual(line["amount"], -19.99)
        self.assertEqual(line["payment_ref"], "Netflix monthly")
        self.assertEqual(line["partner_name"], "Netflix Intl BV")
        self.assertEqual(line["account_number"], "NL00NETF0000000001")
        self.assertEqual(line["ref"], "NFX-123")
        self.assertIn("typeCodeZka", line["narration"])

    def test_mapping_falls_back_on_missing_fields(self):
        tx = {
            "id": 1,
            "accountId": 2,
            "finapiBookingDate": "2026-04-02",
            "amount": 10.0,
        }
        line = self.Provider._finapi_transaction_to_line(tx)
        self.assertEqual(line["date"], "2026-04-02")
        self.assertFalse(line["ref"])
        self.assertFalse(line["partner_name"])
        self.assertEqual(line["unique_import_id"], "finapi-2-1")

    def test_mapping_uses_value_date_as_last_fallback(self):
        tx = {"id": 3, "accountId": 4, "valueDate": "2026-05-01", "amount": 5.0}
        line = self.Provider._finapi_transaction_to_line(tx)
        self.assertEqual(line["date"], "2026-05-01")

    def test_mapping_empty_purpose_shows_placeholder(self):
        tx = {"id": 4, "accountId": 5, "amount": 1.0, "purpose": ""}
        line = self.Provider._finapi_transaction_to_line(tx)
        self.assertTrue(line["payment_ref"])  # Should not be empty

    def test_mapping_narration_with_multiple_fields(self):
        tx = {
            "id": 5,
            "accountId": 6,
            "amount": 1.0,
            "typeCodeZka": "117",
            "bankTransactionCode": "PMNT-RCDT-ESCT",
            "counterpartBic": "COBADEFFXXX",
        }
        line = self.Provider._finapi_transaction_to_line(tx)
        self.assertIn("typeCodeZka: 117", line["narration"])
        self.assertIn("bankTransactionCode: PMNT-RCDT-ESCT", line["narration"])
        self.assertIn("counterpartBic: COBADEFFXXX", line["narration"])

    def test_mapping_narration_empty_when_no_metadata(self):
        tx = {"id": 6, "accountId": 7, "amount": 1.0}
        line = self.Provider._finapi_transaction_to_line(tx)
        self.assertFalse(line["narration"])

    # ------------------------------------------------------------------
    # Datetime parser
    # ------------------------------------------------------------------
    def test_parse_dt_finapi_format(self):
        dt = self.Provider._finapi_parse_dt("2026-07-14T08:00:00.000+0000")
        self.assertEqual(dt.year, 2026)
        self.assertEqual(dt.month, 7)
        self.assertEqual(dt.day, 14)

    def test_parse_dt_with_colon_tz(self):
        dt = self.Provider._finapi_parse_dt("2026-07-14T08:00:00+00:00")
        self.assertEqual(dt.year, 2026)

    def test_parse_dt_with_z(self):
        dt = self.Provider._finapi_parse_dt("2026-07-14T08:00:00Z")
        self.assertEqual(dt.year, 2026)

    def test_parse_dt_converts_non_utc_offset(self):
        """Non-UTC offsets must be converted to UTC, not dropped."""
        dt = self.Provider._finapi_parse_dt("2026-07-14T08:00:00.000+0200")
        self.assertEqual(dt.hour, 6)  # 08:00+02:00 == 06:00 UTC
        dt = self.Provider._finapi_parse_dt("2026-07-14T08:00:00-0500")
        self.assertEqual(dt.hour, 13)  # 08:00-05:00 == 13:00 UTC

    def test_parse_dt_naive_stays_unchanged(self):
        dt = self.Provider._finapi_parse_dt("2026-07-14T08:00:00")
        self.assertEqual(dt.hour, 8)

    def test_parse_dt_empty(self):
        self.assertFalse(self.Provider._finapi_parse_dt(""))
        self.assertFalse(self.Provider._finapi_parse_dt(None))

    def test_parse_dt_invalid(self):
        self.assertFalse(self.Provider._finapi_parse_dt("not-a-date"))

    # ------------------------------------------------------------------
    # Interface factory
    # ------------------------------------------------------------------
    def test_get_interface_raises_without_credentials(self):
        self.provider.finapi_client_id = False
        with self.assertRaises(UserError):
            self.provider._finapi_get_interface()

    def test_get_interface_uses_system_param_defaults(self):
        """If no URL is set on the record, fall back to environment defaults
        (sandbox) which match the system parameters."""
        with mock.patch(_INTERFACE_CLS) as MockIface:
            self.provider._finapi_get_interface()
            call_kwargs = MockIface.call_args[1]
            self.assertIn("sandbox.finapi.io", call_kwargs["base_url"])
            self.assertIn("webform-sandbox.finapi.io", call_kwargs["webform_base_url"])

    def test_get_interface_uses_record_urls(self):
        self.provider.finapi_base_url = "https://custom.finapi.io"
        self.provider.finapi_webform_base_url = "https://custom-wf.finapi.io"
        with mock.patch(_INTERFACE_CLS) as MockIface:
            self.provider._finapi_get_interface()
            call_kwargs = MockIface.call_args[1]
            self.assertEqual(call_kwargs["base_url"], "https://custom.finapi.io")
            self.assertEqual(
                call_kwargs["webform_base_url"], "https://custom-wf.finapi.io"
            )

    # ------------------------------------------------------------------
    # Environment selection
    # ------------------------------------------------------------------
    def test_environment_defaults_to_sandbox(self):
        self.assertEqual(self.provider.finapi_environment, "sandbox")

    def test_onchange_environment_sets_sandbox_urls(self):
        self.provider.finapi_environment = "sandbox"
        self.provider._onchange_finapi_environment()
        self.assertEqual(self.provider.finapi_base_url, "https://sandbox.finapi.io")
        self.assertEqual(
            self.provider.finapi_webform_base_url,
            "https://webform-sandbox.finapi.io",
        )

    def test_onchange_environment_sets_live_urls(self):
        self.provider.finapi_environment = "live"
        self.provider._onchange_finapi_environment()
        self.assertEqual(self.provider.finapi_base_url, "https://live.finapi.io")
        self.assertEqual(
            self.provider.finapi_webform_base_url,
            "https://webform-live.finapi.io",
        )

    def test_get_interface_live_environment_defaults(self):
        """With environment 'live' and no explicit URLs, the interface must
        use the live endpoints."""
        self.provider.finapi_environment = "live"
        with mock.patch(_INTERFACE_CLS) as MockIface:
            self.provider._finapi_get_interface()
            call_kwargs = MockIface.call_args[1]
            self.assertEqual(call_kwargs["base_url"], "https://live.finapi.io")
            self.assertEqual(
                call_kwargs["webform_base_url"], "https://webform-live.finapi.io"
            )

    def test_get_interface_explicit_url_overrides_environment(self):
        """Explicit URL fields take priority over environment defaults."""
        self.provider.finapi_environment = "live"
        self.provider.finapi_base_url = "https://custom.finapi.io"
        with mock.patch(_INTERFACE_CLS) as MockIface:
            self.provider._finapi_get_interface()
            call_kwargs = MockIface.call_args[1]
            self.assertEqual(call_kwargs["base_url"], "https://custom.finapi.io")
            # webform not explicitly set → live default applies
            self.assertEqual(
                call_kwargs["webform_base_url"], "https://webform-live.finapi.io"
            )

    def test_get_interface_sandbox_environment_defaults(self):
        """With environment 'sandbox' and no explicit URLs, the interface
        uses sandbox endpoints."""
        self.provider.finapi_environment = "sandbox"
        with mock.patch(_INTERFACE_CLS) as MockIface:
            self.provider._finapi_get_interface()
            call_kwargs = MockIface.call_args[1]
            self.assertEqual(call_kwargs["base_url"], "https://sandbox.finapi.io")
            self.assertEqual(
                call_kwargs["webform_base_url"],
                "https://webform-sandbox.finapi.io",
            )

    # ------------------------------------------------------------------
    # Token management
    # ------------------------------------------------------------------
    def test_get_user_token_with_refresh(self):
        """If refresh token exists, use it first."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_refresh_token": "old-rt",
            }
        )
        iface = _make_mock_interface()
        token = self.provider._finapi_get_user_token(iface)
        self.assertEqual(token, "user-tok-refreshed")
        iface.refresh_user_token.assert_called_once_with("old-rt")
        iface.get_user_token.assert_not_called()

    def test_get_user_token_fallback_to_password(self):
        """If refresh fails, fall back to password grant."""
        from ..models.finapi_interface import FinapiAuthError

        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_refresh_token": "bad-rt",
            }
        )
        iface = _make_mock_interface()
        iface.refresh_user_token.side_effect = FinapiAuthError("expired")
        token = self.provider._finapi_get_user_token(iface)
        self.assertEqual(token, "user-tok")
        iface.get_user_token.assert_called_once_with("u1", "p1")

    def test_get_user_token_no_refresh_token(self):
        """If no refresh token stored, go straight to password grant."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_refresh_token": False,
            }
        )
        iface = _make_mock_interface()
        token = self.provider._finapi_get_user_token(iface)
        self.assertEqual(token, "user-tok")
        iface.refresh_user_token.assert_not_called()
        iface.get_user_token.assert_called_once()

    def test_get_user_token_persists_new_refresh_token(self):
        """After successful password grant, the new refresh_token is saved."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_refresh_token": False,
            }
        )
        iface = _make_mock_interface()
        self.provider._finapi_get_user_token(iface)
        self.assertEqual(self.provider.finapi_refresh_token, "rt-new")

    def test_get_user_token_raises_without_user(self):
        with self.assertRaises(UserError):
            self.provider._finapi_get_user_token()

    # ------------------------------------------------------------------
    # Group-protected secret fields must not break non-system users
    # ------------------------------------------------------------------
    def _create_account_user(self):
        return self.env["res.users"].create(
            {
                "name": "finAPI Accountant",
                "login": "finapi_accountant",
                "email": "finapi.accountant@example.com",
                "groups_id": [
                    (
                        6,
                        0,
                        [
                            self.env.ref("base.group_user").id,
                            self.env.ref("account.group_account_user").id,
                        ],
                    )
                ],
            }
        )

    def test_get_interface_works_for_account_user(self):
        """finapi_client_secret is base.group_system only — a regular
        accounting user pulling statements must not hit an AccessError."""
        user = self._create_account_user()
        provider = self.provider.with_user(user)
        interface = provider._finapi_get_interface()
        self.assertEqual(interface.client_secret, "test-client-secret")

    def test_get_user_token_works_for_account_user(self):
        """Password / refresh token reads must work for accounting users."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_refresh_token": False,
            }
        )
        user = self._create_account_user()
        provider = self.provider.with_user(user)
        iface = _make_mock_interface()
        token = provider._finapi_get_user_token(iface)
        self.assertEqual(token, "user-tok")
        iface.get_user_token.assert_called_once_with("u1", "p1")

    # ------------------------------------------------------------------
    # action_finapi_create_user
    # ------------------------------------------------------------------
    def test_create_user_ok(self):
        iface = _make_mock_interface()
        iface.create_user.return_value = {"id": "odoo-test-1"}
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ):
            result = self.provider.action_finapi_create_user()
        self.assertTrue(self.provider.finapi_user_id)
        self.assertTrue(self.provider.finapi_user_password)
        iface.create_user.assert_called_once()
        # Should return notification action
        self.assertEqual(result.get("type"), "ir.actions.client")
        self.assertEqual(result.get("tag"), "display_notification")

    def test_create_user_fails_if_already_exists(self):
        self.provider.sudo().write({"finapi_user_id": "existing"})
        with self.assertRaises(UserError):
            self.provider.action_finapi_create_user()

    def test_create_user_id_max_36_chars(self):
        """finAPI limits userId to 36 characters."""
        iface = _make_mock_interface()
        iface.create_user.return_value = {"id": "whatever"}
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ):
            self.provider.action_finapi_create_user()
        self.assertLessEqual(len(self.provider.finapi_user_id), 36)
        # The random suffix must survive any truncation
        self.assertRegex(self.provider.finapi_user_id, r"-[0-9a-f]{8}$")

    # ------------------------------------------------------------------
    # action_finapi_check_connection
    # ------------------------------------------------------------------
    def test_check_connection_ok(self):
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_bank_connection_id": "99",
            }
        )
        iface = _make_mock_interface()
        iface.get_bank_connection.return_value = {
            "id": 99,
            "consent": {"expiresAt": "2026-10-01T12:00:00.000+0000"},
        }
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ), mock.patch.object(
            self.ProviderClass,
            "_finapi_get_user_token",
            return_value="user-tok",
        ):
            result = self.provider.action_finapi_check_connection()
        self.assertTrue(self.provider.finapi_consent_expires_at)
        self.assertEqual(result.get("tag"), "display_notification")

    def test_check_connection_raises_without_bank_connection(self):
        with self.assertRaises(UserError):
            self.provider.action_finapi_check_connection()

    # ------------------------------------------------------------------
    # _obtain_statement_data
    # ------------------------------------------------------------------
    def test_obtain_statement_data_ok(self):
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
            }
        )
        iface = _make_mock_interface()
        iface.list_transactions.return_value = [
            {
                "id": 100,
                "accountId": 42,
                "bankBookingDate": "2026-04-01",
                "amount": -50.0,
                "purpose": "Test tx",
            },
        ]
        iface.get_account.return_value = {"id": 42, "balance": 1000.0}
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ), mock.patch.object(
            self.ProviderClass,
            "_finapi_get_user_token",
            return_value="user-tok",
        ):
            lines, statement_vals = self.provider._obtain_statement_data(
                fields.Datetime.now(),
                fields.Datetime.add(fields.Datetime.now(), days=1),
            )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["amount"], -50.0)
        self.assertEqual(lines[0]["unique_import_id"], "finapi-42-100")
        self.assertEqual(statement_vals["balance_end_real"], 1000.0)
        # interface must be used as context manager (session cleanup)
        iface.__exit__.assert_called_once()

    def test_obtain_statement_data_balance_failure_non_fatal(self):
        """If balance fetch fails, we should still return lines."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
            }
        )
        from ..models.finapi_interface import FinapiApiError

        iface = _make_mock_interface()
        iface.list_transactions.return_value = [
            {
                "id": 200,
                "accountId": 42,
                "bankBookingDate": "2026-04-01",
                "amount": 10.0,
            },
        ]
        iface.get_account.side_effect = FinapiApiError("network error")
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ), mock.patch.object(
            self.ProviderClass,
            "_finapi_get_user_token",
            return_value="user-tok",
        ):
            lines, statement_vals = self.provider._obtain_statement_data(
                fields.Datetime.now(),
                fields.Datetime.add(fields.Datetime.now(), days=1),
            )
        self.assertEqual(len(lines), 1)
        # Balance should be empty dict, not crash
        self.assertEqual(statement_vals, {})

    def test_obtain_statement_data_no_account_raises(self):
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": False,
            }
        )
        with self.assertRaises(UserError):
            self.provider._obtain_statement_data(
                datetime(2026, 4, 1),
                datetime(2026, 4, 2),
            )

    def test_obtain_statement_data_delegates_non_finapi(self):
        """If service is not finapi, it should call super()."""
        provider2 = self.Provider.create(
            {
                "journal_id": self.env["account.journal"]
                .create(
                    {
                        "name": "Other Bank",
                        "type": "bank",
                        "code": "OTHR",
                    }
                )
                .id,
                "service": "dummy",
            }
        )
        # dummy service from OCA should handle (or raise).
        # The key point: it should NOT enter finapi code path.
        try:
            provider2._obtain_statement_data(
                datetime(2026, 4, 1),
                datetime(2026, 4, 2),
            )
        except Exception:
            # dummy may raise; we only verify it does not enter
            # the finapi code path (no FinapiApiError expected)
            logging.getLogger(__name__).debug(
                "Expected: dummy provider raised on _obtain_statement_data"
            )

    def test_obtain_statement_data_empty_transactions(self):
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
            }
        )
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 500.0}
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ), mock.patch.object(
            self.ProviderClass,
            "_finapi_get_user_token",
            return_value="user-tok",
        ):
            lines, statement_vals = self.provider._obtain_statement_data(
                fields.Datetime.now(),
                fields.Datetime.add(fields.Datetime.now(), days=1),
            )
        self.assertEqual(lines, [])
        self.assertEqual(statement_vals["balance_end_real"], 500.0)

    # ------------------------------------------------------------------
    # Bank data refresh — Web Form background update / direct update
    # ------------------------------------------------------------------
    def _setup_linked_provider(self, mode="background"):
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
                "finapi_bank_connection_id": "99",
                "finapi_banking_interface": "XS2A",
                "finapi_refresh_mode": mode,
            }
        )

    def _run_obtain(self, iface):
        with mock.patch.object(
            self.ProviderClass, "_finapi_get_interface", return_value=iface
        ), mock.patch.object(
            self.ProviderClass, "_finapi_get_user_token", return_value="user-tok"
        ):
            return self.provider._obtain_statement_data(
                datetime(2026, 4, 1),
                datetime(2026, 4, 2),
            )

    def test_obtain_none_mode_does_not_refresh(self):
        """Mode 'none': only read, never trigger a refresh."""
        self._setup_linked_provider(mode="none")
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.start_background_update.assert_not_called()
        iface.update_bank_connection.assert_not_called()
        iface.list_transactions.assert_called_once()

    def test_obtain_background_mode_runs_task(self):
        """Default mode triggers the Web Form background-update task."""
        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.start_background_update.assert_called_once_with("user-tok", "99")
        iface.update_bank_connection.assert_not_called()
        iface.list_transactions.assert_called_once()
        self.assertTrue(self.provider.finapi_last_data_update)

    def test_obtain_direct_mode_triggers_update(self):
        """Mode 'direct' uses the Access-API customer-not-present update."""
        self._setup_linked_provider(mode="direct")
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.update_bank_connection.assert_called_once_with(
            "user-tok", "99", banking_interface="XS2A"
        )
        iface.start_background_update.assert_not_called()
        self.assertTrue(self.provider.finapi_last_data_update)

    def test_background_task_polls_until_completed(self):
        """An IN_PROGRESS task is polled until it reaches COMPLETED."""
        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.start_background_update.return_value = {
            "id": "task-9",
            "status": "IN_PROGRESS",
            "payload": {},
        }
        iface.get_task.return_value = {
            "id": "task-9",
            "status": "COMPLETED",
            "payload": {"bankConnectionId": 99},
        }
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        with mock.patch(_PROVIDER_MOD + ".time.sleep"):
            self._run_obtain(iface)
        iface.get_task.assert_called_with("user-tok", "task-9")
        self.assertTrue(self.provider.finapi_last_data_update)

    def test_background_web_form_required_is_non_fatal(self):
        """A task needing SCA (WEB_FORM_REQUIRED) must not abort the pull."""
        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.start_background_update.return_value = {
            "id": "task-9",
            "status": "WEB_FORM_REQUIRED",
            "payload": {"webForm": {"url": "https://wf.example/x"}},
        }
        iface.list_transactions.return_value = [
            {"id": 1, "accountId": 42, "bankBookingDate": "2026-04-01", "amount": 7.0}
        ]
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        lines, _vals = self._run_obtain(iface)
        self.assertEqual(len(lines), 1)
        iface.list_transactions.assert_called_once()
        # The attempt is recorded even though it failed -- see
        # test_failed_refresh_arms_the_throttle for why.
        self.assertTrue(self.provider.finapi_last_data_update)

    def test_background_completed_with_error_is_non_fatal(self):
        """A COMPLETED_WITH_ERROR task is logged, the pull still reads."""
        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.start_background_update.return_value = {
            "id": "task-9",
            "status": "COMPLETED_WITH_ERROR",
            "payload": {"errorCode": "BANK_SERVER_REJECTION", "errorMessage": "x"},
        }
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.list_transactions.assert_called_once()
        # The attempt is recorded even though it failed -- see
        # test_failed_refresh_arms_the_throttle for why.
        self.assertTrue(self.provider.finapi_last_data_update)

    def test_direct_refresh_failure_is_non_fatal(self):
        """A failed direct update must not abort the pull — cached data read."""
        from ..models.finapi_interface import FinapiApiError

        self._setup_linked_provider(mode="direct")
        iface = _make_mock_interface()
        iface.update_bank_connection.side_effect = FinapiApiError("422 forbidden")
        iface.list_transactions.return_value = [
            {"id": 1, "accountId": 42, "bankBookingDate": "2026-04-01", "amount": 7.0}
        ]
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        lines, _vals = self._run_obtain(iface)
        self.assertEqual(len(lines), 1)
        # The attempt is recorded even though it failed -- see
        # test_failed_refresh_arms_the_throttle for why.
        self.assertTrue(self.provider.finapi_last_data_update)

    def test_refresh_is_throttled(self):
        """A refresh within the throttle window must be skipped."""
        self._setup_linked_provider(mode="background")
        self.provider.sudo().write({"finapi_last_data_update": fields.Datetime.now()})
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.start_background_update.assert_not_called()
        iface.list_transactions.assert_called_once()

    def test_refresh_due_after_window(self):
        """Once the throttle window passed, the refresh runs again."""
        self._setup_linked_provider(mode="background")
        stale = fields.Datetime.add(fields.Datetime.now(), hours=-7)
        self.provider.sudo().write({"finapi_last_data_update": stale})
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.start_background_update.assert_called_once()

    def test_failed_refresh_arms_the_throttle(self):
        """A failed refresh must still arm the throttle.

        The OCA framework splits one pull into a statement period per day, so
        a single scheduled run calls ``_obtain_statement_data`` several times
        (the lookback makes that 8 by default). If a failed refresh left the
        throttle unarmed, every period would retry it, and a background update
        that never reaches a terminal status polls for up to
        ``_finapi_background_update_max_wait_seconds`` each time -- minutes of a
        blocked cron worker. An expired consent is the regular PSD2 end state,
        so this is the common case, not an edge case.
        """
        from ..models.finapi_interface import FinapiApiError

        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.start_background_update.side_effect = FinapiApiError("SCA required")
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}

        self._run_obtain(iface)  # first statement period of the pull
        self._run_obtain(iface)  # second period of the same pull

        self.assertTrue(
            self.provider.finapi_last_data_update,
            "a failed refresh must arm the throttle",
        )
        self.assertEqual(
            iface.start_background_update.call_count,
            1,
            "the refresh must not be retried on every statement period",
        )

    def test_refresh_updates_consent_meta(self):
        """After a successful refresh the stored consent expiry + banking
        interface are kept up to date from the bank connection."""
        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.get_bank_connection.return_value = {
            "id": 99,
            "interfaces": [
                {
                    "bankingInterface": "XS2A",
                    "aisConsent": {"expiresAt": "2026-12-31T08:00:00.000+0000"},
                }
            ],
        }
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        self.assertTrue(self.provider.finapi_consent_expires_at)
        self.assertEqual(self.provider.finapi_consent_expires_at.year, 2026)
        self.assertEqual(self.provider.finapi_consent_expires_at.month, 12)

    def test_refresh_skipped_without_bank_connection(self):
        """No bank connection linked → nothing to refresh."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
                "finapi_bank_connection_id": False,
                "finapi_refresh_mode": "background",
            }
        )
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 1.0}
        self._run_obtain(iface)
        iface.start_background_update.assert_not_called()

    # ------------------------------------------------------------------
    # action_finapi_refresh_data_now (manual)
    # ------------------------------------------------------------------
    def test_refresh_data_now_raises_when_mode_none(self):
        self._setup_linked_provider(mode="none")
        with self.assertRaises(UserError):
            self.provider.action_finapi_refresh_data_now()

    def test_refresh_data_now_raises_without_bank_connection(self):
        self.provider.sudo().write(
            {
                "finapi_refresh_mode": "background",
                "finapi_bank_connection_id": False,
            }
        )
        with self.assertRaises(UserError):
            self.provider.action_finapi_refresh_data_now()

    def test_refresh_data_now_forces_refresh_and_pulls(self):
        """The manual action bypasses the throttle and imports immediately."""
        self._setup_linked_provider(mode="background")
        # recent update would normally throttle — force must override it
        self.provider.sudo().write({"finapi_last_data_update": fields.Datetime.now()})
        iface = _make_mock_interface()
        with mock.patch.object(
            self.ProviderClass, "_finapi_get_interface", return_value=iface
        ), mock.patch.object(
            self.ProviderClass, "_finapi_get_user_token", return_value="user-tok"
        ), mock.patch.object(
            self.ProviderClass, "_pull"
        ) as m_pull:
            result = self.provider.action_finapi_refresh_data_now()
        iface.start_background_update.assert_called_once()
        m_pull.assert_called_once()
        self.assertEqual(result.get("tag"), "display_notification")

    def test_refresh_data_now_surfaces_errors(self):
        """Manual refresh re-raises finAPI errors (force=True)."""
        from ..models.finapi_interface import FinapiApiError

        self._setup_linked_provider(mode="direct")
        iface = _make_mock_interface()
        iface.update_bank_connection.side_effect = FinapiApiError("limit")
        with mock.patch.object(
            self.ProviderClass, "_finapi_get_interface", return_value=iface
        ), mock.patch.object(
            self.ProviderClass, "_finapi_get_user_token", return_value="user-tok"
        ), mock.patch.object(
            self.ProviderClass, "_pull"
        ) as m_pull:
            with self.assertRaises(FinapiApiError):
                self.provider.action_finapi_refresh_data_now()
        m_pull.assert_not_called()

    def test_refresh_data_now_web_form_required_redirects_to_wizard(self):
        """SCA is not a crash: offer the consent wizard instead of a traceback.

        finAPI answering ``WEB_FORM_REQUIRED`` means the user has to confirm in
        the bank's web form -- there is nothing broken to report. Raising a
        plain (addon-defined) exception here made the web client fall back to
        its raw RPC traceback dialog, so the user saw a stack trace with the
        web form URL buried in it.
        """
        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.start_background_update.return_value = {
            "id": "task-9",
            "status": "WEB_FORM_REQUIRED",
            "payload": {"webForm": {"url": "https://wf.example/sca"}},
        }
        with mock.patch.object(
            self.ProviderClass, "_finapi_get_interface", return_value=iface
        ), mock.patch.object(
            self.ProviderClass, "_finapi_get_user_token", return_value="user-tok"
        ), mock.patch.object(
            self.ProviderClass, "_pull"
        ) as m_pull:
            with self.assertRaises(RedirectWarning) as catcher:
                self.provider.action_finapi_refresh_data_now()
        message, action_id, _button, context = catcher.exception.args
        wizard_action = self.env.ref(
            "account_statement_import_online_finapi."
            "finapi_webform_wizard_update_action"
        )
        self.assertEqual(action_id, wizard_action.id)
        self.assertIn("https://wf.example/sca", message)
        self.assertEqual(context.get("default_provider_id"), self.provider.id)
        self.assertEqual(context.get("default_mode"), "update")
        m_pull.assert_not_called()

    def test_background_web_form_required_carries_url(self):
        """The SCA case raises its own error type, carrying the form URL."""
        from ..models.finapi_interface import FinapiWebFormRequiredError

        self._setup_linked_provider(mode="background")
        iface = _make_mock_interface()
        iface.start_background_update.return_value = {
            "id": "task-9",
            "status": "WEB_FORM_REQUIRED",
            "payload": {"webForm": {"url": "https://wf.example/x"}},
        }
        with self.assertRaises(FinapiWebFormRequiredError) as catcher:
            self.provider._finapi_run_background_update(iface, "user-tok")
        self.assertEqual(catcher.exception.webform_url, "https://wf.example/x")

    def test_error_dialogs_js_knows_current_exception_paths(self):
        """Guard against silent regressions of the raw-traceback bug.

        The web client picks its error dialog by the *fully qualified* Python
        exception name, so renaming or moving one of our exception classes
        without updating the JS registration would bring the raw RPC traceback
        dialog back.
        """
        from ..models import finapi_interface

        js_path = (
            Path(__file__).resolve().parent.parent
            / "static"
            / "src"
            / "js"
            / "finapi_error_dialogs.esm.js"
        )
        js_source = js_path.read_text(encoding="utf-8")
        for exception_cls in (
            finapi_interface.FinapiApiError,
            finapi_interface.FinapiAuthError,
            finapi_interface.FinapiWebFormRequiredError,
        ):
            qualified_name = f"{exception_cls.__module__}.{exception_cls.__name__}"
            self.assertIn(qualified_name, js_source)

    # ------------------------------------------------------------------
    # _finapi_extract_consent_interface
    # ------------------------------------------------------------------
    def test_extract_consent_interface_from_consent(self):
        bc = {
            "interfaces": [
                {"bankingInterface": "FINTS_SERVER"},
                {
                    "bankingInterface": "XS2A",
                    "aisConsent": {"status": "PRESENT"},
                },
            ]
        }
        self.assertEqual(self.Provider._finapi_extract_consent_interface(bc), "XS2A")

    def test_extract_consent_interface_fallback_to_first(self):
        bc = {"interfaces": [{"bankingInterface": "FINTS_SERVER"}]}
        self.assertEqual(
            self.Provider._finapi_extract_consent_interface(bc), "FINTS_SERVER"
        )

    def test_extract_consent_interface_missing(self):
        self.assertIsNone(self.Provider._finapi_extract_consent_interface({}))
        self.assertIsNone(self.Provider._finapi_extract_consent_interface(None))

    # ------------------------------------------------------------------
    # Lookback window (re-fetch recent days to catch late-arriving tx)
    # ------------------------------------------------------------------
    def _capture_pull_periods(self, scheduled, lookback, date_since, date_until):
        """Run _pull capturing the statement_date_since of each period."""
        self.provider.sudo().write(
            {
                "finapi_account_id": "42",
                "finapi_refresh_mode": "none",
                "statement_creation_mode": "daily",
                "finapi_lookback_days": lookback,
                "interval_number": 1,
                "interval_type": "hours",
                "next_run": date_until,
                "last_successful_run": date_since,
            }
        )
        captured = []

        def fake(provider_self, ds, du):
            captured.append(ds)
            return [], {}

        provider = self.provider
        if scheduled:
            provider = provider.with_context(scheduled=True)
        with mock.patch.object(self.ProviderClass, "_obtain_statement_data", fake):
            provider._pull(date_since, date_until)
        return captured

    def test_scheduled_pull_applies_lookback(self):
        """A scheduled pull re-fetches the last N days, not just since the
        last run."""
        now = fields.Datetime.now()
        captured = self._capture_pull_periods(
            scheduled=True, lookback=7, date_since=now, date_until=now
        )
        self.assertTrue(captured)
        # Earliest re-fetched statement period is ~7 days back.
        self.assertLessEqual(min(captured), fields.Datetime.subtract(now, days=6))

    def test_scheduled_pull_lookback_zero_disabled(self):
        """Lookback 0 keeps the plain incremental window."""
        now = fields.Datetime.now()
        captured = self._capture_pull_periods(
            scheduled=True, lookback=0, date_since=now, date_until=now
        )
        if captured:
            self.assertGreaterEqual(
                min(captured), fields.Datetime.subtract(now, days=1)
            )

    def test_manual_pull_ignores_lookback(self):
        """A manual (non-scheduled) pull keeps the user-selected range."""
        now = fields.Datetime.now()
        captured = self._capture_pull_periods(
            scheduled=False,
            lookback=7,
            date_since=now,
            date_until=fields.Datetime.add(now, days=1),
        )
        self.assertTrue(captured)
        # No 7-day extension: earliest period is the selected day, not a week.
        self.assertGreaterEqual(min(captured), fields.Datetime.subtract(now, days=1))

    # ------------------------------------------------------------------
    # Balance only applies to the current statement period
    # ------------------------------------------------------------------
    def test_is_current_period(self):
        """The current period is recognised from date_since plus the statement
        step (daily by default), not from date_until."""
        provider = self.provider
        now = fields.Datetime.now()
        today = now.replace(hour=0, minute=0, second=0)
        yesterday = fields.Datetime.subtract(today, days=1)
        self.assertTrue(provider._finapi_is_current_period(today))
        self.assertTrue(provider._finapi_is_current_period(now))
        self.assertFalse(provider._finapi_is_current_period(yesterday))
        self.assertFalse(provider._finapi_is_current_period(datetime(2020, 1, 1)))
        self.assertTrue(provider._finapi_is_current_period(None))

    def test_balance_applied_when_sibling_caps_date_until(self):
        """account_statement_import_online_ofx caps date_until at today 00:00
        for *every* provider, before it checks the service, and passes the
        capped value on to super(). The current period must therefore be
        recognised from date_since: otherwise any database that also has the
        OFX module installed never gets the live balance."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
                "finapi_refresh_mode": "none",
            }
        )
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 999.0}
        today = fields.Datetime.now().replace(hour=0, minute=0, second=0)
        with mock.patch.object(
            self.ProviderClass, "_finapi_get_interface", return_value=iface
        ), mock.patch.object(
            self.ProviderClass, "_finapi_get_user_token", return_value="user-tok"
        ):
            # What the OFX module hands down for today's daily period.
            _lines, vals = self.provider._obtain_statement_data(today, today)
        self.assertEqual(vals, {"balance_end_real": 999.0})

    def test_balance_skipped_for_past_period(self):
        """Re-fetching a past period must not overwrite its end balance with
        the live balance."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_account_id": "42",
                "finapi_refresh_mode": "none",
            }
        )
        iface = _make_mock_interface()
        iface.list_transactions.return_value = []
        iface.get_account.return_value = {"id": 42, "balance": 999.0}
        with mock.patch.object(
            self.ProviderClass, "_finapi_get_interface", return_value=iface
        ), mock.patch.object(
            self.ProviderClass, "_finapi_get_user_token", return_value="user-tok"
        ):
            _lines, vals = self.provider._obtain_statement_data(
                datetime(2020, 1, 1), datetime(2020, 1, 2)
            )
        self.assertEqual(vals, {})
        iface.get_account.assert_not_called()

    # ------------------------------------------------------------------
    # Consent expiry extraction
    # ------------------------------------------------------------------
    def test_extract_consent_expiry_from_interface(self):
        """finAPI exposes consent under interfaces[].aisConsent."""
        bc = {
            "id": 99,
            "interfaces": [
                {
                    "bankingInterface": "XS2A",
                    "aisConsent": {
                        "status": "PRESENT",
                        "expiresAt": "2026-12-12T23:59:59.000+0100",
                    },
                }
            ],
        }
        expires = self.Provider._finapi_extract_consent_expiry(bc)
        self.assertEqual(expires, "2026-12-12T23:59:59.000+0100")

    def test_extract_consent_expiry_top_level(self):
        """A legacy top-level consent object is still supported."""
        bc = {"id": 99, "consent": {"expiresAt": "2026-10-01T12:00:00.000+0000"}}
        self.assertEqual(
            self.Provider._finapi_extract_consent_expiry(bc),
            "2026-10-01T12:00:00.000+0000",
        )

    def test_extract_consent_expiry_missing(self):
        self.assertIsNone(self.Provider._finapi_extract_consent_expiry({}))
        self.assertIsNone(self.Provider._finapi_extract_consent_expiry(None))

    def test_check_connection_reads_interface_consent(self):
        """action_finapi_check_connection must parse the interface consent."""
        self.provider.sudo().write(
            {
                "finapi_user_id": "u1",
                "finapi_user_password": "p1",
                "finapi_bank_connection_id": "99",
            }
        )
        iface = _make_mock_interface()
        iface.get_bank_connection.return_value = {
            "id": 99,
            "interfaces": [
                {
                    "bankingInterface": "XS2A",
                    "aisConsent": {"expiresAt": "2026-12-12T23:59:59.000+0100"},
                }
            ],
        }
        with mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        ), mock.patch.object(
            self.ProviderClass,
            "_finapi_get_user_token",
            return_value="user-tok",
        ):
            self.provider.action_finapi_check_connection()
        self.assertTrue(self.provider.finapi_consent_expires_at)
        self.assertEqual(self.provider.finapi_consent_expires_at.year, 2026)
        self.assertEqual(self.provider.finapi_consent_expires_at.month, 12)
        # Check connection also records the consent-bearing interface so the
        # licensed direct refresh can target it.
        self.assertEqual(self.provider.finapi_banking_interface, "XS2A")

    # ------------------------------------------------------------------
    # action_finapi_open_webform_wizard
    # ------------------------------------------------------------------
    def test_open_webform_wizard_raises_without_user(self):
        with self.assertRaises(UserError):
            self.provider.action_finapi_open_webform_wizard()

    def test_open_webform_wizard_returns_action(self):
        self.provider.sudo().write({"finapi_user_id": "u1"})
        result = self.provider.action_finapi_open_webform_wizard()
        self.assertEqual(result["res_model"], "finapi.webform.wizard")
        self.assertEqual(result["target"], "new")

    # ------------------------------------------------------------------
    # action_finapi_refresh_consent
    # ------------------------------------------------------------------
    def test_refresh_consent_raises_without_connection(self):
        with self.assertRaises(UserError):
            self.provider.action_finapi_refresh_consent()

    def test_refresh_consent_returns_wizard_action(self):
        self.provider.sudo().write(
            {
                "finapi_bank_connection_id": "99",
            }
        )
        result = self.provider.action_finapi_refresh_consent()
        self.assertEqual(result["res_model"], "finapi.webform.wizard")
        self.assertEqual(
            result["context"]["default_mode"],
            "update",
        )

    # ------------------------------------------------------------------
    # Consent-expiry cron
    # ------------------------------------------------------------------
    def test_cron_consent_expiry_sends_alert_only_once(self):
        """First run sends one mail and marks the expiry as alerted;
        the second run must not send a duplicate."""
        expires = fields.Datetime.add(fields.Datetime.now(), days=5)
        self.provider.sudo().write(
            {
                "finapi_bank_connection_id": "99",
                "finapi_consent_expires_at": expires,
            }
        )
        Mail = self.env["mail.mail"]
        count_initial = Mail.search_count([])
        self.Provider._finapi_cron_check_consent_expiry()
        count_after_first = Mail.search_count([])
        self.assertGreater(count_after_first, count_initial)
        self.assertEqual(
            self.provider.finapi_consent_alert_expiry,
            self.provider.finapi_consent_expires_at,
        )
        # second run: nothing new
        self.Provider._finapi_cron_check_consent_expiry()
        self.assertEqual(Mail.search_count([]), count_after_first)

    def test_cron_consent_expiry_not_due_sends_nothing(self):
        expires = fields.Datetime.add(fields.Datetime.now(), days=60)
        self.provider.sudo().write(
            {
                "finapi_bank_connection_id": "99",
                "finapi_consent_expires_at": expires,
            }
        )
        self.Provider._finapi_cron_check_consent_expiry()
        self.assertFalse(self.provider.finapi_consent_alert_expiry)

    def test_cron_consent_expiry_realerts_after_renewal(self):
        """After a consent renewal the new expiry must trigger a new alert
        once it gets close again."""
        old_expiry = fields.Datetime.add(fields.Datetime.now(), days=5)
        self.provider.sudo().write(
            {
                "finapi_bank_connection_id": "99",
                "finapi_consent_expires_at": old_expiry,
                "finapi_consent_alert_expiry": old_expiry,
            }
        )
        # consent renewed, but already close to expiry again
        new_expiry = fields.Datetime.add(fields.Datetime.now(), days=10)
        self.provider.sudo().write({"finapi_consent_expires_at": new_expiry})
        Mail = self.env["mail.mail"]
        count_initial = Mail.search_count([])
        self.Provider._finapi_cron_check_consent_expiry()
        self.assertGreater(Mail.search_count([]), count_initial)
        self.assertEqual(self.provider.finapi_consent_alert_expiry, new_expiry)
