# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json

import plaid
from plaid.api import plaid_api
from plaid.model.accounts_get_request import AccountsGetRequest
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.item_remove_request import ItemRemoveRequest
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from odoo import models
from odoo.exceptions import UserError, ValidationError


def _to_dict(record):
    return record.to_dict() if hasattr(record, "to_dict") else dict(record)


class PlaidInterface(models.AbstractModel):
    _name = "plaid.interface"
    _description = "Plaid Interface"

    def _get_host(self, host):
        if host == "sandbox":
            return plaid.Environment.Sandbox
        if host == "production":
            return plaid.Environment.Production
        return False

    def _raise(self, what, exception):
        """Turn a Plaid API error into a readable message."""
        try:
            body = json.loads(exception.body)
        except (TypeError, ValueError):
            body = {}
        if body.get("error_code") == "ITEM_LOGIN_REQUIRED":
            raise UserError(
                self.env._(
                    "The bank login has expired or changed. Click 'Reconnect Bank' "
                    "on the provider."
                )
            ) from exception
        message = body.get("display_message") or body.get("error_message")
        if body.get("error_code") == "INVALID_API_KEYS":
            # Plaid has one secret per environment, and they are easy to mix up.
            message = self.env._(
                "%(message)s. Check that the Secret Key is the one for the "
                "selected Plaid Host: Sandbox and Production secrets differ.",
                message=message,
            )
        raise ValidationError(
            self.env._(
                "%(what)s: %(message)s",
                what=what,
                message=message or exception.body,
            )
        ) from exception

    def _client(self, client_id, secret, host):
        configuration = plaid.Configuration(
            host=self._get_host(host),
            api_key={
                "clientId": client_id or "",
                "secret": secret or "",
            },
        )
        try:
            return plaid_api.PlaidApi(plaid.ApiClient(configuration))
        except plaid.ApiException as e:
            self._raise(self.env._("Error getting client api"), e)

    def _link(
        self, client, language, country_code, company_name, products, access_token=None
    ):
        """Create a Link token. With an access token, Link opens in update
        mode to repair an existing login instead of adding a new one."""
        values = {
            "client_name": company_name,
            "country_codes": [CountryCode(country_code)],
            "language": language,
            "user": LinkTokenCreateRequestUser(client_user_id="client"),
        }
        if access_token:
            values["access_token"] = access_token
        else:
            values["products"] = [Products(product) for product in products]
        try:
            response = client.link_token_create(LinkTokenCreateRequest(**values))
        except plaid.ApiException as e:
            self._raise(self.env._("Error getting link token"), e)
        return response.to_dict()["link_token"]

    def _login(self, client, public_token):
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        try:
            response = client.item_public_token_exchange(request)
        except plaid.ApiException as e:
            self._raise(self.env._("Error getting access token"), e)
        return response["access_token"]

    def _remove(self, client, access_token):
        """Remove a login at Plaid, which ends its billing."""
        try:
            client.item_remove(ItemRemoveRequest(access_token=access_token))
        except plaid.ApiException as e:
            self._raise(self.env._("Error removing the bank login"), e)

    def _get_accounts(self, client, access_token):
        """Return the accounts of a login, as dicts."""
        try:
            response = client.accounts_get(
                AccountsGetRequest(access_token=access_token)
            )
        except plaid.ApiException as e:
            self._raise(self.env._("Error getting accounts"), e)
        return [_to_dict(account) for account in response["accounts"]]

    def _get_transactions(
        self, client, access_token, start_date, end_date, account_ids=None
    ):
        """Return all transactions from start_date to end_date (both dates
        included), as dicts. Without account_ids, every account of the login
        is included."""

        def fetch(offset):
            options = TransactionsGetRequestOptions(count=500, offset=offset)
            if account_ids:
                options.account_ids = list(account_ids)
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date,
                end_date=end_date,
                options=options,
            )
            try:
                return client.transactions_get(request)
            except plaid.ApiException as e:
                self._raise(self.env._("Error getting transactions"), e)

        response = fetch(0)
        transactions = list(response["transactions"])
        while (
            response["transactions"]
            and len(transactions) < response["total_transactions"]
        ):
            response = fetch(len(transactions))
            transactions.extend(response["transactions"])
        return [_to_dict(transaction) for transaction in transactions]
