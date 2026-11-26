# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime
from unittest.mock import MagicMock, patch

import plaid
from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.tests import common

from .test_account_statement_import_online_plaid import TRANSACTIONS


class TestPlaidInterface(common.TransactionCase):
    post_install = True

    def test_get_host(self):
        """Test getting Plaid host."""
        interface_model = self.env["plaid.interface"]
        self.assertEqual(
            interface_model._get_host("sandbox"), plaid.Environment.Sandbox
        )
        self.assertEqual(
            interface_model._get_host("production"), plaid.Environment.Production
        )
        self.assertFalse(interface_model._get_host("nonexistent"))

    @patch("plaid.api.plaid_api.PlaidApi")
    def test_client(self, PlaidApi):
        interface_model = self.env["plaid.interface"]
        PlaidApi.return_value = MagicMock()
        client = interface_model._client("client_id", "secret", "sandbox")
        self.assertTrue(client)

    @patch(
        "plaid.api.plaid_api.PlaidApi",
        side_effect=plaid.ApiException("INVALID_SECRET", "This secret is invalid"),
    )
    def test_client_error(self, PlaidApi):
        interface_model = self.env["plaid.interface"]
        self.assertRaises(
            ValidationError, interface_model._client, "client_id", "secret2", "sandbox"
        )

    @patch("plaid.api.plaid_api.PlaidApi.link_token_create")
    def test_link(self, link_token_create):
        interface_model = self.env["plaid.interface"]
        link_token_create.return_value = MagicMock(
            to_dict=lambda: {"link_token": "isalinktoken", "expiration": "isadate"}
        )
        client = interface_model._client("client_id", "secret", "sandbox")
        link = interface_model._link(
            client=client,
            language="en",
            country_code="US",
            company_name="company",
            products=["transactions"],
        )
        self.assertTrue(link)
        self.assertEqual(link, "isalinktoken")

    @patch(
        "plaid.api.plaid_api.PlaidApi.link_token_create",
        side_effect=plaid.ApiException(
            "INVALID_CLIENT_ID", "This client id is invalid"
        ),
    )
    def test_link_error(self, link_token_create):
        interface_model = self.env["plaid.interface"]
        client = interface_model._client("client_id", "secret", "sandbox")
        self.assertRaises(
            ValidationError,
            interface_model._link,
            client,
            "en",
            "US",
            "company",
            ["transactions"],
        )

    @patch("plaid.api.plaid_api.PlaidApi.item_public_token_exchange")
    def test_login(self, item_public_token_exchange):
        interface_model = self.env["plaid.interface"]
        item_public_token_exchange.return_value = MagicMock(
            to_dict=lambda: {"access_token": "isaccesstoken"}
        )
        client = interface_model._client("client_id", "secret", "sandbox")
        public_token = "isapulbictoken"
        access_token = interface_model._login(client, public_token)
        self.assertTrue(access_token)

    @patch(
        "plaid.api.plaid_api.PlaidApi.item_public_token_exchange",
        side_effect=plaid.ApiException("INVALID_PUBLIC_TOKEN", "This token is invalid"),
    )
    def test_login_error(self, item_public_token_exchange):
        interface_model = self.env["plaid.interface"]
        client = interface_model._client("client_id", "secret", "sandbox")
        public_token = "isapulbictoken"
        self.assertRaises(ValidationError, interface_model._login, client, public_token)

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_get_transactions(self, transactions_get):
        interface_model = self.env["plaid.interface"]
        client = interface_model._client("client_id", "secret", "sandbox")
        transactions_get.return_value = {
            "transactions": TRANSACTIONS,
            "total_transactions": len(TRANSACTIONS),
        }

        access_token = "isaccesstoken"
        start_date = datetime.datetime.now() - relativedelta(months=1)
        end_date = datetime.datetime.now()
        res = interface_model._get_transactions(
            client, access_token, start_date, end_date
        )

        self.assertTrue(res)

    @patch(
        "plaid.api.plaid_api.PlaidApi.transactions_get",
        side_effect=plaid.ApiException(
            "INVALID_ACCESS_TOKEN", "This access token is invalid"
        ),
    )
    def test_get_transactions_error(self, transactions_get):
        interface_model = self.env["plaid.interface"]
        client = interface_model._client("client_id", "secret", "sandbox")
        access_token = "isaccesstoken"
        start_date = datetime.datetime.now() - relativedelta(months=1)
        end_date = datetime.datetime.now()
        self.assertRaises(
            ValidationError,
            interface_model._get_transactions,
            client,
            access_token,
            start_date,
            end_date,
        )
