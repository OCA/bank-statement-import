# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime
from unittest.mock import MagicMock, patch

import plaid
import urllib3
from dateutil.relativedelta import relativedelta
from urllib3.util import Retry

from odoo.exceptions import ValidationError
from odoo.tests import common

from .test_account_statement_import_online_plaid import TRANSACTIONS


class TestPlaidInterface(common.TransactionCase):
    post_install = True

    def test_http_rejects_sdk_redirects(self):
        interface = self.env["plaid.interface"]
        for host in ("sandbox", "production"):
            client = interface._client("dummy-client", "dummy-secret", host)
            try:
                for status in (301, 302, 303, 307, 308):
                    for target in (
                        "http://127.0.0.1/private",
                        "https://untrusted.invalid/",
                    ):
                        response = urllib3.HTTPResponse(
                            status=status, headers={"Location": target}, body=b"{}"
                        )
                        # urllib3 carries the connection's retry policy on the response.
                        response.retries = client.api_client.configuration.retries
                        with (
                            self.subTest(host=host, status=status, target=target),
                            patch(
                                "urllib3.connectionpool.HTTPSConnectionPool._make_request",
                                side_effect=[
                                    response,
                                    AssertionError("Redirect followed"),
                                ],
                            ) as https,
                            patch(
                                "urllib3.connectionpool.HTTPConnectionPool._make_request"
                            ) as http,
                            self.assertRaisesRegex(
                                ValidationError, "Error getting access token"
                            ),
                        ):
                            try:
                                interface._login(client, "dummy-public-token")
                            finally:
                                https.assert_called_once()
                                http.assert_not_called()
            finally:
                client.api_client.close()

    def test_http_preserves_hosts_credentials_and_retries(self):
        interface = self.env["plaid.interface"]
        for host, hostname in (
            ("sandbox", "sandbox.plaid.com"),
            ("production", "production.plaid.com"),
        ):
            client = interface._client("dummy-client", "dummy-secret", host)
            try:
                response = urllib3.HTTPResponse(
                    status=200,
                    body=b'{"access_token":"dummy-access","item_id":"dummy-item","request_id":"dummy-request"}',
                )
                with patch(
                    "urllib3.connectionpool.HTTPSConnectionPool._make_request",
                    return_value=response,
                ) as transport:
                    self.assertEqual(
                        interface._login(client, "dummy-public-token"), "dummy-access"
                    )
                self.assertEqual(
                    client.api_client.configuration.host, f"https://{hostname}"
                )
                transport.assert_called_once()
                request_headers = transport.call_args.kwargs["headers"]
                self.assertEqual(request_headers["PLAID-CLIENT-ID"], "dummy-client")
                self.assertEqual(request_headers["PLAID-SECRET"], "dummy-secret")
                retries = client.api_client.rest_client.pool_manager.connection_pool_kw[
                    "retries"
                ]
                self.assertEqual(retries.total, Retry.DEFAULT.total)
                self.assertEqual(retries.connect, Retry.DEFAULT.connect)
                self.assertEqual(retries.read, Retry.DEFAULT.read)
                self.assertEqual(retries.redirect, 0)
            finally:
                client.api_client.close()

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
