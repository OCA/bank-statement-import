# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
from unittest.mock import MagicMock, patch

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import common

from .test_account_statement_import_online_ponto import FOUR_TRANSACTIONS


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
            access_data["ponto_account"], "2ad3df83-be01-47cf-a6be-cf0de5cb4c99"
        )

    @patch("requests.get")
    def test_get_transactions(self, requests_get):
        """Test getting transactions from Ponto."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        # Key "data" will contain a list of transactions.
        mock_response.text = json.dumps({"data": FOUR_TRANSACTIONS})
        requests_get.return_value = mock_response
        # Start of actual test.
        access_data = self._get_access_dict()
        interface_model = self.env["ponto.interface"]
        transactions = interface_model._get_transactions(access_data, False)
        self.assertEqual(len(transactions), 4)
        self.assertEqual(transactions[3]["id"], "b21a6c65-1c52-4ba6-8cbc-127d2b2d85ff")
        self.assertEqual(
            transactions[3]["attributes"]["counterpartReference"], "BE10325927501996"
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
