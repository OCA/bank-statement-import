# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime
import json
from unittest.mock import MagicMock, patch

import plaid

from odoo.exceptions import UserError, ValidationError
from odoo.tests import common

from .test_account_statement_import_online_plaid import TRANSACTIONS

START = datetime.date(2024, 5, 1)
END = datetime.date(2024, 6, 30)


class TestPlaidInterface(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.interface = cls.env["plaid.interface"]
        cls.client = cls.interface._client("client_id", "secret", "sandbox")

    def test_get_host(self):
        self.assertEqual(self.interface._get_host("sandbox"), plaid.Environment.Sandbox)
        self.assertEqual(
            self.interface._get_host("production"), plaid.Environment.Production
        )
        self.assertFalse(self.interface._get_host("nonexistent"))

    @patch(
        "plaid.api.plaid_api.PlaidApi",
        side_effect=plaid.ApiException("INVALID_SECRET", "This secret is invalid"),
    )
    def test_client_error(self, PlaidApi):
        self.assertRaises(
            ValidationError, self.interface._client, "client_id", "secret2", "sandbox"
        )

    @patch("plaid.api.plaid_api.PlaidApi.link_token_create")
    def test_link(self, link_token_create):
        link_token_create.return_value = MagicMock(
            to_dict=lambda: {"link_token": "isalinktoken", "expiration": "isadate"}
        )
        link = self.interface._link(
            client=self.client,
            language="en",
            country_code="US",
            company_name="company",
            products=["transactions"],
        )
        self.assertEqual(link, "isalinktoken")
        request = link_token_create.call_args.args[0]
        self.assertEqual([str(p) for p in request.products], ["transactions"])

    @patch("plaid.api.plaid_api.PlaidApi.link_token_create")
    def test_link_update_mode(self, link_token_create):
        link_token_create.return_value = MagicMock(
            to_dict=lambda: {"link_token": "isalinktoken"}
        )
        self.interface._link(
            self.client, "en", "US", "company", ["transactions"], access_token="tok"
        )
        request = link_token_create.call_args.args[0]
        self.assertEqual(request.access_token, "tok")
        self.assertNotIn("products", request)

    @patch(
        "plaid.api.plaid_api.PlaidApi.link_token_create",
        side_effect=plaid.ApiException(
            "INVALID_CLIENT_ID", "This client id is invalid"
        ),
    )
    def test_link_error(self, link_token_create):
        self.assertRaises(
            ValidationError,
            self.interface._link,
            self.client,
            "en",
            "US",
            "company",
            ["transactions"],
        )

    @patch("plaid.api.plaid_api.PlaidApi.item_public_token_exchange")
    def test_login(self, item_public_token_exchange):
        item_public_token_exchange.return_value = {"access_token": "isaccesstoken"}
        self.assertEqual(
            self.interface._login(self.client, "isapublictoken"), "isaccesstoken"
        )

    @patch(
        "plaid.api.plaid_api.PlaidApi.item_public_token_exchange",
        side_effect=plaid.ApiException("INVALID_PUBLIC_TOKEN", "This token is invalid"),
    )
    def test_login_error(self, item_public_token_exchange):
        self.assertRaises(
            ValidationError, self.interface._login, self.client, "isapublictoken"
        )

    @patch("plaid.api.plaid_api.PlaidApi.accounts_get")
    def test_get_accounts(self, accounts_get):
        accounts_get.return_value = {"accounts": [{"account_id": "a1", "name": "A"}]}
        self.assertEqual(
            self.interface._get_accounts(self.client, "tok"),
            [{"account_id": "a1", "name": "A"}],
        )

    @patch("plaid.api.plaid_api.PlaidApi.item_remove")
    def test_remove(self, item_remove):
        self.interface._remove(self.client, "tok")
        self.assertEqual(item_remove.call_args.args[0].access_token, "tok")

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_get_transactions(self, transactions_get):
        transactions_get.return_value = {
            "transactions": TRANSACTIONS,
            "total_transactions": len(TRANSACTIONS),
        }
        res = self.interface._get_transactions(
            self.client, "tok", START, END, account_ids=["checking"]
        )
        self.assertEqual(len(res), len(TRANSACTIONS))
        request = transactions_get.call_args.args[0]
        self.assertEqual((request.start_date, request.end_date), (START, END))
        self.assertEqual(request.options.account_ids, ["checking"])

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_get_transactions_pages(self, transactions_get):
        transactions_get.side_effect = [
            {"transactions": TRANSACTIONS[:1], "total_transactions": 2},
            {"transactions": TRANSACTIONS[1:2], "total_transactions": 2},
        ]
        res = self.interface._get_transactions(self.client, "tok", START, END)
        self.assertEqual(len(res), 2)
        self.assertEqual(transactions_get.call_args.args[0].options.offset, 1)

    @patch(
        "plaid.api.plaid_api.PlaidApi.transactions_get",
        side_effect=plaid.ApiException(
            "INVALID_ACCESS_TOKEN", "This access token is invalid"
        ),
    )
    def test_get_transactions_error(self, transactions_get):
        self.assertRaises(
            ValidationError,
            self.interface._get_transactions,
            self.client,
            "tok",
            START,
            END,
        )

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_login_required(self, transactions_get):
        error = plaid.ApiException(status=400, reason="Bad Request")
        error.body = json.dumps({"error_code": "ITEM_LOGIN_REQUIRED"})
        transactions_get.side_effect = error
        with self.assertRaisesRegex(UserError, "Reconnect Bank"):
            self.interface._get_transactions(self.client, "tok", START, END)

    @patch("plaid.api.plaid_api.PlaidApi.link_token_create")
    def test_invalid_keys_hint(self, link_token_create):
        error = plaid.ApiException(status=400, reason="Bad Request")
        error.body = json.dumps(
            {
                "error_code": "INVALID_API_KEYS",
                "error_message": "invalid client_id or secret provided",
            }
        )
        link_token_create.side_effect = error
        with self.assertRaisesRegex(ValidationError, "Sandbox and Production"):
            self.interface._link(self.client, "en", "US", "company", ["transactions"])
