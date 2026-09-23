# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
"""Unit tests for the pure finAPI REST wrapper (no Odoo environment needed)."""
from unittest import mock

from odoo.tests.common import TransactionCase, tagged

from ..models.finapi_interface import FinapiApiError, FinapiAuthError, FinapiInterface


def _mock_response(status_code=200, json_body=None, headers=None, text=""):
    resp = mock.Mock()
    resp.status_code = status_code
    resp.content = b"x" if json_body is not None or text else b""
    resp.text = text or ""
    resp.headers = headers or {}
    resp.json = mock.Mock(return_value=json_body or {})
    return resp


@tagged("post_install", "-at_install")
class TestFinapiInterface(TransactionCase):
    def setUp(self):
        super().setUp()
        self.interface = FinapiInterface(
            base_url="https://sandbox.finapi.io",
            client_id="cid",
            client_secret="csec",
            webform_base_url="https://webform-sandbox.finapi.io",
        )
        # deterministic session cleanup — do not rely on __del__/GC
        self.addCleanup(self.interface.close)

    def _patch(self, *responses):
        """Patch the internal session's .request() to return the given
        responses in order."""
        return mock.patch.object(
            self.interface._session,
            "request",
            side_effect=list(responses),
        )

    # ------------------------------------------------------------------
    # OAuth — v2-scoped clients require /api/v2 prefix
    # ------------------------------------------------------------------
    def test_client_token_ok(self):
        with self._patch(_mock_response(200, {"access_token": "abc"})) as m:
            self.assertEqual(self.interface.get_client_token(), "abc")
            url = m.call_args[0][1]
            self.assertIn("/api/v2/oauth/token", url)

    def test_user_token_returns_full_payload(self):
        payload = {"access_token": "at", "refresh_token": "rt", "expires_in": 3600}
        with self._patch(_mock_response(200, payload)):
            self.assertEqual(
                self.interface.get_user_token("u", "p"),
                payload,
            )

    def test_refresh_user_token_ok(self):
        payload = {"access_token": "new_at", "refresh_token": "new_rt"}
        with self._patch(_mock_response(200, payload)):
            result = self.interface.refresh_user_token("old_rt")
            self.assertEqual(result["access_token"], "new_at")

    def test_auth_error_401_raises_auth_error(self):
        with self._patch(_mock_response(401, text="bad token")):
            with self.assertRaises(FinapiAuthError):
                self.interface.get_bank_connection("badtoken", 1)

    def test_generic_error_raises_api_error(self):
        body = {"errors": [{"message": "nope"}]}
        with self._patch(_mock_response(400, body, text="x")):
            with self.assertRaises(FinapiApiError) as cm:
                self.interface.get_bank_connection("t", 1)
            self.assertIn("nope", str(cm.exception))

    def test_connection_error_raises_api_error(self):
        """requests.RequestException should be wrapped in FinapiApiError."""
        import requests as req

        with mock.patch.object(
            self.interface._session,
            "request",
            side_effect=req.ConnectionError("refused"),
        ):
            with self.assertRaises(FinapiApiError):
                self.interface.get_client_token()

    # ------------------------------------------------------------------
    # Transactions pagination
    # ------------------------------------------------------------------
    def test_list_transactions_paginates(self):
        page1 = {
            "transactions": [{"id": 1}, {"id": 2}],
            "paging": {"page": 1, "pageCount": 2},
        }
        page2 = {
            "transactions": [{"id": 3}],
            "paging": {"page": 2, "pageCount": 2},
        }
        with self._patch(
            _mock_response(200, page1),
            _mock_response(200, page2),
        ):
            out = self.interface.list_transactions(
                "tok",
                42,
                "2026-01-01",
                "2026-01-31",
            )
        self.assertEqual([t["id"] for t in out], [1, 2, 3])

    def test_list_transactions_single_page(self):
        page = {
            "transactions": [{"id": 1}],
            "paging": {"page": 1, "pageCount": 1},
        }
        with self._patch(_mock_response(200, page)):
            out = self.interface.list_transactions(
                "tok",
                42,
                "2026-01-01",
                "2026-01-31",
            )
        self.assertEqual(len(out), 1)

    def test_list_transactions_empty(self):
        page = {
            "transactions": [],
            "paging": {"page": 1, "pageCount": 1},
        }
        with self._patch(_mock_response(200, page)):
            out = self.interface.list_transactions(
                "tok",
                42,
                "2026-01-01",
                "2026-01-31",
            )
        self.assertEqual(out, [])

    # ------------------------------------------------------------------
    # Web Form — separate host (webform_base_url), no /api/v2 prefix
    # ------------------------------------------------------------------
    def test_create_webform_import(self):
        body = {
            "id": "wf-1",
            "url": "https://webform-sandbox.finapi.io/wf/wf-1",
            "status": "NOT_YET_OPENED",
        }
        with self._patch(_mock_response(201, body)) as m:
            out = self.interface.create_webform_import(
                "tok",
                redirect_url="https://x/return",
            )
        self.assertEqual(out["id"], "wf-1")
        url = m.call_args[0][1]
        self.assertTrue(
            url.startswith("https://webform-sandbox.finapi.io"),
            f"Expected webform host, got: {url}",
        )
        self.assertIn("/api/webForms/bankConnectionImport", url)

    def test_create_webform_import_no_language_field(self):
        """The body must NOT include a 'language' field (causes 400)."""
        body = {"id": "wf-1", "url": "https://x/wf/wf-1"}
        with self._patch(_mock_response(201, body)) as m:
            self.interface.create_webform_import("tok")
        call_kwargs = m.call_args[1]
        sent_body = call_kwargs.get("json") or {}
        self.assertNotIn("language", sent_body)

    def test_create_webform_update(self):
        body = {"id": "wf-2", "url": "https://x/wf/wf-2"}
        with self._patch(_mock_response(201, body)) as m:
            self.interface.create_webform_update("tok", 123)
        # Must use PUT (not POST) per Web Form 2.0 API
        method = m.call_args[0][0]
        self.assertEqual(method, "PUT")
        url = m.call_args[0][1]
        self.assertTrue(
            url.startswith("https://webform-sandbox.finapi.io"),
            f"Expected webform host, got: {url}",
        )
        self.assertIn("/api/webForms/bankConnectionUpdate", url)

    def test_get_webform(self):
        body = {"id": "wf-1", "status": "COMPLETED"}
        with self._patch(_mock_response(200, body)) as m:
            self.interface.get_webform("tok", "wf-1")
        url = m.call_args[0][1]
        self.assertTrue(
            url.startswith("https://webform-sandbox.finapi.io"),
            f"Expected webform host, got: {url}",
        )
        self.assertIn("/api/webForms/wf-1", url)

    def test_webform_base_url_defaults_to_base_url(self):
        """If webform_base_url is not given, it falls back to base_url."""
        iface = FinapiInterface(
            base_url="https://sandbox.finapi.io",
            client_id="cid",
            client_secret="csec",
        )
        self.addCleanup(iface.close)
        self.assertEqual(iface.webform_base_url, "https://sandbox.finapi.io")

    # ------------------------------------------------------------------
    # User management
    # ------------------------------------------------------------------
    def test_create_user(self):
        body = {"id": "odoo-test-1", "password": "pw123"}
        with self._patch(_mock_response(201, body)):
            out = self.interface.create_user(
                "client_tok", user_id="odoo-test-1", password="pw123"
            )
        self.assertEqual(out["id"], "odoo-test-1")

    # ------------------------------------------------------------------
    # Account / bank connection
    # ------------------------------------------------------------------
    def test_get_account(self):
        body = {"id": 42, "balance": 1234.56, "iban": "DE89370400440532013000"}
        with self._patch(_mock_response(200, body)):
            out = self.interface.get_account("tok", 42)
        self.assertEqual(out["balance"], 1234.56)

    def test_list_accounts(self):
        body = {"accounts": [{"id": 1}, {"id": 2}]}
        with self._patch(_mock_response(200, body)):
            out = self.interface.list_accounts("tok", 99)
        self.assertEqual(len(out), 2)

    def test_get_bank_connection(self):
        body = {"id": 99, "consent": {"expiresAt": "2026-07-14T08:00:00.000+0000"}}
        with self._patch(_mock_response(200, body)):
            out = self.interface.get_bank_connection("tok", 99)
        self.assertEqual(out["id"], 99)

    # ------------------------------------------------------------------
    # Bank connection update (licensed mandators)
    # ------------------------------------------------------------------
    def test_update_bank_connection_posts_correct_payload(self):
        body = {"id": 99, "consent": {"expiresAt": "2026-10-01T08:00:00.000+0000"}}
        with self._patch(_mock_response(200, body)) as m:
            out = self.interface.update_bank_connection(
                "tok", 99, banking_interface="XS2A"
            )
        self.assertEqual(out["id"], 99)
        method = m.call_args[0][0]
        url = m.call_args[0][1]
        self.assertEqual(method, "POST")
        self.assertIn("/api/v2/bankConnections/update", url)
        sent_body = m.call_args[1].get("json") or {}
        self.assertEqual(
            sent_body, {"bankConnectionId": 99, "bankingInterface": "XS2A"}
        )

    def test_update_bank_connection_omits_interface_when_missing(self):
        with self._patch(_mock_response(200, {"id": 99})) as m:
            self.interface.update_bank_connection("tok", 99)
        sent_body = m.call_args[1].get("json") or {}
        self.assertEqual(sent_body, {"bankConnectionId": 99})

    def test_update_bank_connection_casts_id_to_int(self):
        """finAPI ids are stored as Char in Odoo; must be sent as int64."""
        with self._patch(_mock_response(200, {"id": 99})) as m:
            self.interface.update_bank_connection("tok", "85465787")
        sent_body = m.call_args[1].get("json") or {}
        self.assertEqual(sent_body["bankConnectionId"], 85465787)

    def test_update_bank_connection_uses_longer_timeout(self):
        from ..models.finapi_interface import UPDATE_TIMEOUT

        with self._patch(_mock_response(200, {"id": 99})) as m:
            self.interface.update_bank_connection("tok", 99)
        # The bank round-trip is slow — must not use the short default.
        self.assertEqual(m.call_args[1].get("timeout"), UPDATE_TIMEOUT)

    def test_update_bank_connection_auth_error(self):
        with self._patch(_mock_response(401, text="consent expired")):
            with self.assertRaises(FinapiAuthError):
                self.interface.update_bank_connection("tok", 99)

    def test_update_bank_connection_api_error(self):
        """Unlicensed mandators get a 4xx 'use the Web Form' rejection."""
        body = {"errors": [{"message": "direct API calls not allowed"}]}
        with self._patch(_mock_response(422, body, text="x")):
            with self.assertRaises(FinapiApiError):
                self.interface.update_bank_connection("tok", 99, "XS2A")

    # ------------------------------------------------------------------
    # Web Form 2.0 background update task
    # ------------------------------------------------------------------
    def test_start_background_update_posts_to_task_endpoint(self):
        body = {"id": "task-1", "status": "IN_PROGRESS", "payload": {}}
        with self._patch(_mock_response(201, body)) as m:
            out = self.interface.start_background_update("tok", "85465787")
        self.assertEqual(out["id"], "task-1")
        method, url = m.call_args[0][0], m.call_args[0][1]
        self.assertEqual(method, "POST")
        self.assertIn("/api/tasks/backgroundUpdate", url)
        # must go to the Web Form host, and cast the id to int64
        self.assertIn("webform-sandbox.finapi.io", url)
        self.assertEqual(m.call_args[1].get("json"), {"bankConnectionId": 85465787})

    def test_start_background_update_includes_callbacks(self):
        with self._patch(_mock_response(201, {"id": "t"})) as m:
            self.interface.start_background_update(
                "tok", 99, redirect_url="https://x/r", callback_url="https://x/c"
            )
        sent = m.call_args[1].get("json")
        self.assertEqual(sent["redirectUrl"], "https://x/r")
        self.assertEqual(sent["callbacks"]["finalised"], "https://x/c")
        self.assertEqual(sent["callbacks"]["webFormRequired"], "https://x/c")

    def test_get_task_reads_from_webform_host(self):
        body = {"id": "task-1", "status": "COMPLETED", "payload": {}}
        with self._patch(_mock_response(200, body)) as m:
            out = self.interface.get_task("tok", "task-1")
        self.assertEqual(out["status"], "COMPLETED")
        url = m.call_args[0][1]
        self.assertIn("/api/tasks/task-1", url)
        self.assertIn("webform-sandbox.finapi.io", url)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------
    def test_close_releases_session(self):
        with mock.patch.object(self.interface._session, "close") as m_close:
            self.interface.close()
        m_close.assert_called_once()

    def test_context_manager_closes_session(self):
        iface = FinapiInterface(
            base_url="https://sandbox.finapi.io",
            client_id="cid",
            client_secret="csec",
        )
        self.addCleanup(iface.close)
        with mock.patch.object(iface._session, "close") as m_close:
            with iface as entered:
                self.assertIs(entered, iface)
        m_close.assert_called_once()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def test_pretty(self):
        result = FinapiInterface.pretty({"key": "value"})
        self.assertIn("key", result)
        self.assertIn("value", result)
