# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
"""HTTP tests for the finAPI Web Form return page and webhook callback."""
import json

from odoo.tests.common import HttpCase, tagged


@tagged("post_install", "-at_install")
class TestFinapiController(HttpCase):
    def setUp(self):
        super().setUp()
        # Bind an anonymous session to this database. Without it the
        # session-less test requests cannot infer the db when several
        # databases exist on the cluster and would 404 on module routes.
        self.authenticate(None, None)
        self.webhook_secret = "test-webhook-secret"
        self.env["ir.config_parameter"].sudo().set_param(
            "finapi.webhook_secret", self.webhook_secret
        )
        self.journal = self.env["account.journal"].create(
            {
                "name": "finAPI Controller Test",
                "type": "bank",
                "code": "FCTL",
            }
        )
        self.provider = self.env["online.bank.statement.provider"].create(
            {
                "journal_id": self.journal.id,
                "service": "finapi",
                "finapi_client_id": "cid",
                "finapi_client_secret": "csec",
                "finapi_last_webform_id": "wf-callback-test",
            }
        )

    def _post_callback(self, payload, secret=None):
        if secret is None:
            secret = self.webhook_secret
        url = "/finapi/webform/callback"
        if secret:
            url += f"?secret={secret}"
        return self.url_open(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
        )

    def test_return_page(self):
        """The landing page is a translatable QWeb template on web.layout,
        not an HTML string in the controller."""
        resp = self.url_open("/finapi/webform/return")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(b"Authorisation completed", resp.content)
        self.assertIn(b"<title>finAPI: authorisation completed</title>", resp.content)

    def test_callback_missing_secret_returns_403(self):
        resp = self._post_callback(
            json.dumps({"webFormId": "wf-callback-test", "status": "COMPLETED"}),
            secret="",
        )
        self.assertEqual(resp.status_code, 403)

    def test_callback_wrong_secret_returns_403(self):
        resp = self._post_callback(
            json.dumps({"webFormId": "wf-callback-test", "status": "COMPLETED"}),
            secret="wrong-secret",
        )
        self.assertEqual(resp.status_code, 403)

    def test_callback_unconfigured_secret_returns_403(self):
        """Without a configured webhook secret every callback is rejected."""
        self.env["ir.config_parameter"].sudo().set_param("finapi.webhook_secret", "")
        resp = self._post_callback(
            json.dumps({"webFormId": "wf-callback-test", "status": "COMPLETED"}),
            secret="anything",
        )
        self.assertEqual(resp.status_code, 403)

    def test_callback_invalid_json_returns_400(self):
        resp = self._post_callback(b"this is not json")
        self.assertEqual(resp.status_code, 400)

    def test_callback_non_object_json_returns_400(self):
        resp = self._post_callback(b'"just a string"')
        self.assertEqual(resp.status_code, 400)

    def test_callback_unknown_webform_ok(self):
        resp = self._post_callback(
            json.dumps({"webFormId": "does-not-exist", "status": "COMPLETED"})
        )
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok"})

    def test_callback_posts_chatter_message(self):
        """A callback for a known web form must log a note on the provider
        — even though the route needs no session (auth='public')."""
        messages_before = len(self.provider.message_ids)
        resp = self._post_callback(
            json.dumps({"webFormId": "wf-callback-test", "status": "COMPLETED"})
        )
        self.assertEqual(resp.status_code, 200)
        self.provider.invalidate_recordset(["message_ids"])
        self.assertEqual(len(self.provider.message_ids), messages_before + 1)
        self.assertIn("COMPLETED", self.provider.message_ids[0].body)

    def test_callback_escapes_html(self):
        """Attacker-controlled values must be escaped in the chatter."""
        resp = self._post_callback(
            json.dumps(
                {
                    "webFormId": "wf-callback-test",
                    "status": "<script>alert(1)</script>",
                }
            )
        )
        self.assertEqual(resp.status_code, 200)
        self.provider.invalidate_recordset(["message_ids"])
        body = self.provider.message_ids[0].body
        self.assertNotIn("<script>", body)
