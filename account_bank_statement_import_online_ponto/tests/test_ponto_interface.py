# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from dateutil.relativedelta import relativedelta
import json

from unittest.mock import MagicMock, patch

from odoo import fields
from odoo.tests import common

from .test_account_statement_import_online_ponto import THREE_TRANSACTIONS


class TestPontoInterface(common.TransactionCase):
    post_install = True

    @patch("requests.post")
    def test_login(self, requests_post):
        """Check Ponto API login."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "access_token": "live_the_token",
                "expires_in": 1799,
                "scope": "ai",
                "token_type": "bearer",
            }
        )
        requests_post.return_value = mock_response
        interface_model = self.env["ponto.interface"]
        access_data = interface_model._login("uncle_john", "secret")
        self.assertEqual(access_data["access_token"], "live_the_token")
        self.assertIn("token_expiration", access_data)

    @patch("requests.get")
    def test_set_access_account(self, requests_get):
        """Test getting account data for Ponto access."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps(
            {
                "data": [
                    {
                        "id": "wrong_id",
                        "attributes": {
                            "reference": "NL66ABNA123456789",
                        },
                    },
                    {
                        "id": "2ad3df83-be01-47cf-a6be-cf0de5cb4c99",
                        "attributes": {
                            "reference": "NL66RABO123456789",
                        },
                    },
                ],
            }
        )
        requests_get.return_value = mock_response
        # Start of actual test.
        access_data = self._get_access_dict(include_account=False)
        interface_model = self.env["ponto.interface"]
        interface_model._set_access_account(access_data, "NL66RABO123456789")
        self.assertIn("ponto_account", access_data)
        self.assertEqual(
            access_data["ponto_account"],
            "2ad3df83-be01-47cf-a6be-cf0de5cb4c99"
        )

    @patch("requests.post")
    def test_ponto_synchronisation(self, requests_post):
        """Test requesting Ponto synchronization."""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = json.dumps(
            {
                "errors": [
                    {
                        "code": "accountRecentlySynchronized",
                        "detail":
                            "This type of synchronization was already created recently"
                            " for the account. Try again later or on the Dashboard.",
                        "meta": {}
                    }
                ]
            }
        )
        requests_post.return_value = mock_response
        # Start of actual test (succeeds if no Exceptions occur).
        access_data = self._get_access_dict()
        interface_model = self.env["ponto.interface"]
        interface_model._ponto_synchronisation(access_data)

    @patch("requests.get")
    def test_synchronization_done(self, requests_get):
        """Test getting account data for Ponto access."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = json.dumps({"status": "success"})
        requests_get.return_value = mock_response
        # Succesfull sync.
        self._check_synchronization_done(True)
        # Error in sync.
        mock_response.text = json.dumps({"status": "error"})
        self._check_synchronization_done(True)
        # Unexpected error in sync.
        mock_response.status_code = 404
        self._check_synchronization_done(False)

    def _check_synchronization_done(self, expected_result):
        """Check result for synchronization with current mock."""
        interface_model = self.env["ponto.interface"]
        access_data = self._get_access_dict()
        synchronization_done = interface_model._synchronization_done(
            access_data,
            "https//does.not.matter.com/synchronization"
        )
        self.assertEqual(synchronization_done, expected_result)

    @patch("requests.get")
    def test_get_transactions(self, requests_get):
        """Test getting transactions from Ponto."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Key "data" will contain a list of transactions.
        mock_response.text = json.dumps({"data": THREE_TRANSACTIONS})
        requests_get.return_value = mock_response
        # Start of actual test.
        access_data = self._get_access_dict()
        interface_model = self.env["ponto.interface"]
        transactions = interface_model._get_transactions(access_data, False)
        self.assertEqual(len(transactions), 3)
        self.assertEqual(transactions[2]["id"], "b21a6c65-1c52-4ba6-8cbc-127d2b2d85ff")
        self.assertEqual(
            transactions[2]["attributes"]["counterpartReference"],
            "BE10325927501996"
        )

    def _get_access_dict(self, include_account=True):
        """Get access dict that caches login/account information."""
        token_expiration = fields.Datetime.now() + relativedelta(seconds=1800)
        access_data = {
            "username": "uncle_john",
            "password": "secret",
            "access_token": "live_the_token",
            "token_expiration": token_expiration,
        }
        if include_account:
            access_data["ponto_account"] = "2ad3df83-be01-47cf-a6be-cf0de5cb4c99"
        return access_data
