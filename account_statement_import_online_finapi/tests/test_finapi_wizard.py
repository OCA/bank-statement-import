# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
"""Tests for the finAPI Web Form 2.0 wizard state machine.

All external HTTP calls are mocked.

Note: Odoo recordset methods live on the *class*, not the instance — so we
patch at ``type(recordset)`` level to avoid the "read-only" attribute error.
"""
from unittest import mock

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged


def _make_mock_interface():
    """Return a MagicMock mimicking FinapiInterface."""
    iface = mock.MagicMock()
    # context manager: `with iface as x:` must yield the mock itself
    iface.__enter__.return_value = iface
    iface.get_client_token.return_value = "client-tok"
    iface.get_user_token.return_value = {
        "access_token": "user-tok",
        "refresh_token": "rt-new",
    }
    iface.refresh_user_token.return_value = {
        "access_token": "user-tok-r",
        "refresh_token": "rt-r",
    }
    return iface


@tagged("post_install", "-at_install")
class TestFinapiWebformWizard(TransactionCase):
    def setUp(self):
        super().setUp()
        self.journal = self.env["account.journal"].create(
            {
                "name": "finAPI Wizard Test",
                "type": "bank",
                "code": "FWIZ",
            }
        )
        self.provider = self.env["online.bank.statement.provider"].create(
            {
                "journal_id": self.journal.id,
                "service": "finapi",
                "finapi_client_id": "test-cid",
                "finapi_client_secret": "test-csec",
                "finapi_user_id": "test-user",
                "finapi_user_password": "test-pass",
            }
        )
        self.ProviderClass = type(self.provider)
        self.Wizard = self.env["finapi.webform.wizard"]

    def _create_wizard(self, **kwargs):
        vals = {
            "provider_id": self.provider.id,
            "mode": "import",
        }
        vals.update(kwargs)
        return self.Wizard.create(vals)

    def _patch_provider(self, iface):
        """Return a combined context manager that patches the provider's
        _finapi_get_interface and _finapi_get_user_token at the class level."""
        return mock.patch.object(
            self.ProviderClass,
            "_finapi_get_interface",
            return_value=iface,
        )

    def _patch_provider_token(self):
        return mock.patch.object(
            self.ProviderClass,
            "_finapi_get_user_token",
            return_value="user-tok",
        )

    # ------------------------------------------------------------------
    # Step 1: action_start (import mode)
    # ------------------------------------------------------------------
    def test_action_start_import(self):
        wiz = self._create_wizard()
        iface = _make_mock_interface()
        iface.create_webform_import.return_value = {
            "id": "wf-import-1",
            "url": "https://webform-sandbox.finapi.io/wf/wf-import-1",
            "status": "NOT_YET_OPENED",
        }
        with self._patch_provider(iface), self._patch_provider_token():
            result = wiz.action_start()
        self.assertEqual(wiz.state, "waiting")
        self.assertEqual(wiz.webform_id, "wf-import-1")
        self.assertTrue(wiz.webform_url)
        self.assertEqual(wiz.webform_status, "NOT_YET_OPENED")
        self.assertEqual(self.provider.finapi_last_webform_id, "wf-import-1")
        iface.create_webform_import.assert_called_once()
        # interface must be used as context manager (session cleanup)
        iface.__exit__.assert_called_once()
        # Should return an action to reopen the wizard
        self.assertEqual(result["res_model"], "finapi.webform.wizard")

    # ------------------------------------------------------------------
    # Step 1: action_start (update mode)
    # ------------------------------------------------------------------
    def test_action_start_update(self):
        self.provider.sudo().write({"finapi_bank_connection_id": "99"})
        wiz = self._create_wizard(mode="update")
        iface = _make_mock_interface()
        iface.create_webform_update.return_value = {
            "id": "wf-update-1",
            "url": "https://webform-sandbox.finapi.io/wf/wf-update-1",
            "status": "NOT_YET_OPENED",
        }
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_start()
        self.assertEqual(wiz.state, "waiting")
        iface.create_webform_update.assert_called_once()
        # bank_connection_id should have been passed
        call_args = iface.create_webform_update.call_args
        self.assertEqual(call_args[0][1], "99")  # second positional arg

    def test_action_start_update_falls_back_to_import_on_api_error(self):
        """If bankConnectionUpdate is rejected by finAPI, fall back to a
        fresh bankConnectionImport web form."""
        from ..models.finapi_interface import FinapiApiError

        self.provider.sudo().write({"finapi_bank_connection_id": "99"})
        wiz = self._create_wizard(mode="update")
        iface = _make_mock_interface()
        iface.create_webform_update.side_effect = FinapiApiError("not updatable")
        iface.create_webform_import.return_value = {
            "id": "wf-fallback-1",
            "url": "https://webform-sandbox.finapi.io/wf/wf-fallback-1",
            "status": "NOT_YET_OPENED",
        }
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_start()
        self.assertEqual(wiz.state, "waiting")
        self.assertEqual(wiz.webform_id, "wf-fallback-1")
        iface.create_webform_import.assert_called_once()

    def test_action_start_import_retries_without_redirect_when_unlicensed(self):
        """UNLICENSED (sandbox) mandators reject redirectUrl with a 422 —
        the wizard must transparently retry without redirect/callback."""
        from ..models.finapi_interface import FinapiApiError

        # https base url so that redirect/callback URLs are generated
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.com"
        )
        wiz = self._create_wizard()
        iface = _make_mock_interface()
        iface.create_webform_import.side_effect = [
            FinapiApiError(
                'finAPI error 422: {"code":"INVALID_REDIRECT_URL",'
                '"description":"Parameter \'redirectUrl\' is provided, but '
                "not allowed as mandator's license is UNLICENSED.\"}"
            ),
            {
                "id": "wf-retry-1",
                "url": "https://webform-sandbox.finapi.io/wf/wf-retry-1",
                "status": "NOT_YET_OPENED",
            },
        ]
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_start()
        self.assertEqual(wiz.state, "waiting")
        self.assertEqual(wiz.webform_id, "wf-retry-1")
        self.assertEqual(iface.create_webform_import.call_count, 2)
        # first call carried the redirect URL, the retry must not
        first_kwargs = iface.create_webform_import.call_args_list[0][1]
        retry_kwargs = iface.create_webform_import.call_args_list[1][1]
        self.assertTrue(first_kwargs.get("redirect_url"))
        self.assertFalse(retry_kwargs.get("redirect_url"))
        self.assertFalse(retry_kwargs.get("callback_url"))

    def test_action_start_update_retries_without_redirect_when_unlicensed(self):
        """Same license retry for the consent-renewal (update) web form;
        it must NOT fall back to an import web form in that case."""
        from ..models.finapi_interface import FinapiApiError

        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.com"
        )
        self.provider.sudo().write({"finapi_bank_connection_id": "99"})
        wiz = self._create_wizard(mode="update")
        iface = _make_mock_interface()
        iface.create_webform_update.side_effect = [
            FinapiApiError('{"code":"INVALID_REDIRECT_URL"}'),
            {
                "id": "wf-upd-retry-1",
                "url": "https://webform-sandbox.finapi.io/wf/wf-upd-retry-1",
                "status": "NOT_YET_OPENED",
            },
        ]
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_start()
        self.assertEqual(wiz.state, "waiting")
        self.assertEqual(wiz.webform_id, "wf-upd-retry-1")
        self.assertEqual(iface.create_webform_update.call_count, 2)
        iface.create_webform_import.assert_not_called()

    def test_webform_urls_carry_webhook_secret(self):
        """The callback URL must contain the auto-generated shared secret;
        the user-facing return URL must not."""
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param("web.base.url", "https://odoo.example.com")
        icp.set_param("finapi.webhook_secret", False)
        wiz = self._create_wizard()
        redirect_url, callback_url = wiz._get_webform_urls()
        secret = icp.get_param("finapi.webhook_secret")
        self.assertTrue(secret, "secret must be auto-generated on first use")
        self.assertEqual(
            callback_url,
            f"https://odoo.example.com/finapi/webform/callback?secret={secret}",
        )
        self.assertEqual(redirect_url, "https://odoo.example.com/finapi/webform/return")
        # second call reuses the same secret
        _redirect, callback_url2 = wiz._get_webform_urls()
        self.assertEqual(callback_url, callback_url2)

    def test_webform_urls_empty_without_https(self):
        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "http://insecure.example.com"
        )
        wiz = self._create_wizard()
        self.assertEqual(wiz._get_webform_urls(), (None, None))

    def test_action_start_import_other_api_error_propagates(self):
        """A non-license API error must not trigger the redirect retry."""
        from ..models.finapi_interface import FinapiApiError

        self.env["ir.config_parameter"].sudo().set_param(
            "web.base.url", "https://odoo.example.com"
        )
        wiz = self._create_wizard()
        iface = _make_mock_interface()
        iface.create_webform_import.side_effect = FinapiApiError("server error 500")
        with self._patch_provider(iface), self._patch_provider_token():
            with self.assertRaises(FinapiApiError):
                wiz.action_start()
        self.assertEqual(iface.create_webform_import.call_count, 1)

    def test_action_start_update_auth_error_propagates(self):
        """Auth errors must NOT silently fall back — credentials are broken
        and the user has to know."""
        from ..models.finapi_interface import FinapiAuthError

        self.provider.sudo().write({"finapi_bank_connection_id": "99"})
        wiz = self._create_wizard(mode="update")
        iface = _make_mock_interface()
        iface.create_webform_update.side_effect = FinapiAuthError("bad token")
        with self._patch_provider(iface), self._patch_provider_token():
            with self.assertRaises(FinapiAuthError):
                wiz.action_start()
        iface.create_webform_import.assert_not_called()

    # ------------------------------------------------------------------
    # Step 2: action_refresh — COMPLETED
    # ------------------------------------------------------------------
    def test_action_refresh_completed(self):
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {
            "status": "COMPLETED",
            "payload": {"bankConnectionId": 77},
        }
        iface.list_accounts.return_value = [
            {
                "id": 101,
                "iban": "DE89370400440532013000",
                "accountHolderName": "Test GmbH",
                "accountTypeName": "Checking",
                "balance": 5000.0,
                "currency": "EUR",
            },
            {
                "id": 102,
                "iban": "DE89370400440532013001",
                "accountHolderName": "Test GmbH",
                "accountTypeName": "Savings",
                "balance": 10000.0,
                "currency": "EUR",
            },
        ]
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "account_select")
        self.assertEqual(wiz.bank_connection_id, "77")
        self.assertEqual(len(wiz.account_ids), 2)
        # Check account details
        acc1 = wiz.account_ids.filtered(lambda a: a.finapi_account_id == "101")
        self.assertEqual(acc1.iban, "DE89370400440532013000")
        self.assertEqual(acc1.balance, 5000.0)

    # ------------------------------------------------------------------
    # Step 2: action_refresh — still in progress
    # ------------------------------------------------------------------
    def test_action_refresh_in_progress(self):
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {"status": "IN_PROGRESS"}
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "waiting")  # Should stay in waiting
        self.assertEqual(wiz.webform_status, "IN_PROGRESS")

    def test_action_refresh_escapes_status(self):
        """``info`` is an Html field with sanitize=False, and the status comes
        from the finAPI response — it must be escaped before interpolation."""
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {"status": "<script>alert(1)</script>"}
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertNotIn("<script>", wiz.info)
        self.assertIn("&lt;script&gt;", wiz.info)

    # ------------------------------------------------------------------
    # Step 2: action_refresh — error states
    # ------------------------------------------------------------------
    def test_action_refresh_aborted(self):
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {"status": "ABORTED"}
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "done")

    def test_action_refresh_expired(self):
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {"status": "EXPIRED"}
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "done")

    def test_action_refresh_completed_with_error(self):
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {"status": "COMPLETED_WITH_ERROR"}
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "done")

    # ------------------------------------------------------------------
    # Step 2: action_refresh — no webform_id
    # ------------------------------------------------------------------
    def test_action_refresh_no_webform_raises(self):
        wiz = self._create_wizard()
        with self.assertRaises(UserError):
            wiz.action_refresh()

    # ------------------------------------------------------------------
    # Step 2: action_refresh — COMPLETED but no bankConnectionId
    # ------------------------------------------------------------------
    def test_action_refresh_completed_no_bc_id_raises(self):
        wiz = self._create_wizard()
        wiz.write({"state": "waiting", "webform_id": "wf-1"})
        iface = _make_mock_interface()
        iface.get_webform.return_value = {
            "status": "COMPLETED",
            "payload": {},
        }
        with self._patch_provider(iface), self._patch_provider_token():
            with self.assertRaises(UserError):
                wiz.action_refresh()

    # ------------------------------------------------------------------
    # Step 3: action_apply
    # ------------------------------------------------------------------
    def test_action_apply_ok(self):
        wiz = self._create_wizard()
        wiz.write(
            {
                "state": "account_select",
                "bank_connection_id": "77",
            }
        )
        acc = self.env["finapi.webform.wizard.account"].create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "101",
                "iban": "DE89370400440532013000",
                "name": "Test GmbH",
                "account_type": "Checking",
                "balance": 5000.0,
                "currency": "EUR",
            }
        )
        wiz.selected_account_id = acc.id
        # Mock the check_connection that runs at the end
        with mock.patch.object(
            self.ProviderClass,
            "action_finapi_check_connection",
            return_value={"type": "ir.actions.client"},
        ):
            wiz.action_apply()
        self.assertEqual(wiz.state, "done")
        self.assertEqual(self.provider.finapi_bank_connection_id, "77")
        self.assertEqual(self.provider.finapi_account_id, "101")

    def test_action_apply_no_selection_raises(self):
        wiz = self._create_wizard()
        wiz.write({"state": "account_select"})
        with self.assertRaises(UserError):
            wiz.action_apply()

    # ------------------------------------------------------------------
    # Step 3: action_apply with multi_link
    # ------------------------------------------------------------------
    def test_action_apply_multi_link(self):
        """First account goes to the current provider; every additional
        account gets its own journal + auto-linked provider with copied
        finAPI credentials."""
        wiz = self._create_wizard()
        wiz.write(
            {
                "state": "account_select",
                "bank_connection_id": "77",
                "multi_link": True,
            }
        )
        Account = self.env["finapi.webform.wizard.account"]
        Account.create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "101",
                "iban": "DE89370400440532013000",
                "currency": "EUR",
            }
        )
        Account.create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "102",
                "iban": "DE89370400440532013001",
                "currency": "EUR",
            }
        )
        with mock.patch.object(
            self.ProviderClass,
            "action_finapi_check_connection",
            return_value={"type": "ir.actions.client"},
        ):
            wiz.action_apply()
        self.assertEqual(wiz.state, "done")
        # first account → original provider
        self.assertEqual(self.provider.finapi_account_id, "101")
        self.assertEqual(self.provider.finapi_bank_connection_id, "77")
        # second account → new journal + provider
        new_provider = self.env["online.bank.statement.provider"].search(
            [
                ("service", "=", "finapi"),
                ("finapi_account_id", "=", "102"),
            ]
        )
        self.assertEqual(len(new_provider), 1)
        self.assertNotEqual(new_provider, self.provider)
        self.assertEqual(new_provider.finapi_bank_connection_id, "77")
        # journal must be properly linked to the provider (OCA linkage)
        journal = new_provider.journal_id
        self.assertEqual(journal.type, "bank")
        self.assertEqual(journal.bank_statements_source, "online")
        self.assertEqual(journal.online_bank_statement_provider_id, new_provider)
        # credentials copied from the source provider
        self.assertEqual(new_provider.finapi_client_id, "test-cid")
        self.assertEqual(new_provider.sudo().finapi_client_secret, "test-csec")
        self.assertEqual(new_provider.finapi_user_id, "test-user")
        self.assertEqual(new_provider.sudo().finapi_user_password, "test-pass")

    def test_action_apply_multi_link_copies_environment(self):
        """The finapi_environment must be copied to the new provider so a
        live setup stays live when adding further accounts."""
        self.provider.sudo().write({"finapi_environment": "live"})
        wiz = self._create_wizard()
        wiz.write(
            {
                "state": "account_select",
                "bank_connection_id": "77",
                "multi_link": True,
            }
        )
        Account = self.env["finapi.webform.wizard.account"]
        Account.create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "201",
                "iban": "DE00000000000000000010",
                "currency": "EUR",
            }
        )
        Account.create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "202",
                "iban": "DE00000000000000000011",
                "currency": "EUR",
            }
        )
        with mock.patch.object(
            self.ProviderClass,
            "action_finapi_check_connection",
            return_value={"type": "ir.actions.client"},
        ):
            wiz.action_apply()
        new_provider = self.env["online.bank.statement.provider"].search(
            [
                ("service", "=", "finapi"),
                ("finapi_account_id", "=", "202"),
            ]
        )
        self.assertEqual(len(new_provider), 1)
        self.assertEqual(new_provider.finapi_environment, "live")

    def test_action_apply_multi_link_no_accounts_raises(self):
        wiz = self._create_wizard()
        wiz.write({"state": "account_select", "multi_link": True})
        with self.assertRaises(UserError):
            wiz.action_apply()

    def test_get_or_create_provider_for_journal_fallback(self):
        """If the OCA auto-creation did not link a provider, the helper
        must create and link one itself."""
        wiz = self._create_wizard()
        journal = self.env["account.journal"].create(
            {
                "name": "finAPI Fallback",
                "type": "bank",
                "code": "FFBK",
            }
        )
        self.assertFalse(journal.online_bank_statement_provider_id)
        provider = wiz._get_or_create_provider_for_journal(journal)
        self.assertTrue(provider)
        self.assertEqual(provider.service, "finapi")
        self.assertEqual(provider.journal_id, journal)
        self.assertEqual(journal.online_bank_statement_provider_id, provider)
        # idempotent: second call returns the same provider
        self.assertEqual(wiz._get_or_create_provider_for_journal(journal), provider)

    def test_action_apply_consent_check_failure_non_fatal(self):
        """If consent check fails after apply, it should not raise."""
        wiz = self._create_wizard()
        wiz.write(
            {
                "state": "account_select",
                "bank_connection_id": "77",
            }
        )
        acc = self.env["finapi.webform.wizard.account"].create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "101",
                "iban": "DE00000000000000000001",
            }
        )
        wiz.selected_account_id = acc.id
        with mock.patch.object(
            self.ProviderClass,
            "action_finapi_check_connection",
            side_effect=UserError("network error"),
        ):
            # Should not raise
            wiz.action_apply()
        self.assertEqual(wiz.state, "done")
        self.assertEqual(self.provider.finapi_account_id, "101")

    # ------------------------------------------------------------------
    # Wizard account name_get
    # ------------------------------------------------------------------
    def test_wizard_account_name_get(self):
        wiz = self._create_wizard()
        acc = self.env["finapi.webform.wizard.account"].create(
            {
                "wizard_id": wiz.id,
                "finapi_account_id": "101",
                "iban": "DE89370400440532013000",
                "name": "Test GmbH",
                "account_type": "Checking",
            }
        )
        display = acc.name_get()
        self.assertEqual(len(display), 1)
        self.assertIn("DE89370400440532013000", display[0][1])
        self.assertIn("Checking", display[0][1])

    # ------------------------------------------------------------------
    # Full wizard flow (integration)
    # ------------------------------------------------------------------
    def test_full_wizard_flow(self):
        """Test the complete wizard flow: start -> refresh -> apply."""
        wiz = self._create_wizard()
        iface = _make_mock_interface()

        # Step 1: Start
        iface.create_webform_import.return_value = {
            "id": "wf-full-1",
            "url": "https://webform-sandbox.finapi.io/wf/wf-full-1",
            "status": "NOT_YET_OPENED",
        }
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_start()
        self.assertEqual(wiz.state, "waiting")

        # Step 2: Refresh (still in progress)
        iface.get_webform.return_value = {"status": "IN_PROGRESS"}
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "waiting")

        # Step 2: Refresh (completed)
        iface.get_webform.return_value = {
            "status": "COMPLETED",
            "payload": {"bankConnectionId": 55},
        }
        iface.list_accounts.return_value = [
            {
                "id": 201,
                "iban": "DE00000000000000000001",
                "accountHolderName": "Firma",
                "balance": 100.0,
                "currency": "EUR",
            },
        ]
        with self._patch_provider(iface), self._patch_provider_token():
            wiz.action_refresh()
        self.assertEqual(wiz.state, "account_select")
        self.assertEqual(len(wiz.account_ids), 1)

        # Step 3: Apply
        wiz.selected_account_id = wiz.account_ids[0].id
        with mock.patch.object(
            self.ProviderClass,
            "action_finapi_check_connection",
            return_value={"type": "ir.actions.client"},
        ):
            wiz.action_apply()
        self.assertEqual(wiz.state, "done")
        self.assertEqual(self.provider.finapi_bank_connection_id, "55")
        self.assertEqual(self.provider.finapi_account_id, "201")
