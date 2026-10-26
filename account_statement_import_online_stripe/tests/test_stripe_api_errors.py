# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import io
import json
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from odoo.exceptions import UserError
from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon

MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe"
)


def _http_error(code, body=None, headers=None):
    return HTTPError(
        "https://api.stripe.com/v1/balance_transactions",
        code,
        "Error",
        headers or {},
        io.BytesIO(json.dumps(body or {}).encode()),
    )


def _response(body):
    return io.BytesIO(json.dumps(body).encode())


class TestStripeApiErrors(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        journal = cls.env["account.journal"].create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": journal.id,
            }
        )

    def _api_get(self, responses):
        with (
            patch(f"{MODULE}.urllib.request.urlopen", side_effect=responses) as urlopen,
            patch(f"{MODULE}.time.sleep") as sleep,
            mute_logger(MODULE),
        ):
            try:
                result = self.provider._stripe_api_get("/balance_transactions")
            except UserError as error:
                result = error
        return result, urlopen, sleep

    def test_retry_rate_limit(self):
        result, urlopen, sleep = self._api_get(
            [
                _http_error(429),
                _http_error(429),
                _response({"data": [], "has_more": False}),
            ]
        )
        self.assertEqual(result, {"data": [], "has_more": False})
        self.assertEqual(urlopen.call_count, 3)
        self.assertEqual([call.args[0] for call in sleep.call_args_list], [1, 2])

    def test_retry_network_error(self):
        result, urlopen, sleep = self._api_get(
            [URLError("timed out"), _response({"data": [], "has_more": False})]
        )
        self.assertEqual(result, {"data": [], "has_more": False})
        self.assertEqual(urlopen.call_count, 2)

    def test_retry_after_header(self):
        result, urlopen, sleep = self._api_get(
            [
                _http_error(503, headers={"Retry-After": "5"}),
                _response({"data": [], "has_more": False}),
            ]
        )
        self.assertEqual(sleep.call_args.args[0], 5)

    def test_retry_exhausted(self):
        result, urlopen, sleep = self._api_get([_http_error(429)] * 4)
        self.assertIsInstance(result, UserError)
        self.assertEqual(urlopen.call_count, 4)

    def test_no_retry_when_stripe_says_so(self):
        result, urlopen, sleep = self._api_get(
            [_http_error(500, headers={"Stripe-Should-Retry": "false"})]
        )
        self.assertIsInstance(result, UserError)
        self.assertEqual(urlopen.call_count, 1)
        sleep.assert_not_called()

    def test_readable_error(self):
        result, urlopen, sleep = self._api_get(
            [
                _http_error(
                    401,
                    body={
                        "error": {
                            "message": "Invalid API Key provided: rk_live_****abcd",
                            "type": "invalid_request_error",
                        }
                    },
                    headers={"Request-Id": "req_123"},
                )
            ]
        )
        self.assertIsInstance(result, UserError)
        self.assertEqual(urlopen.call_count, 1)
        self.assertEqual(
            str(result),
            "Stripe API call failed: /balance_transactions: Invalid API Key "
            "provided: rk_live_****abcd (type: invalid_request_error, "
            "request: req_123)",
        )
