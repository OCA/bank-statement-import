# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import plaid
from plaid.api import plaid_api
from plaid.model.country_code import CountryCode
from plaid.model.item_public_token_exchange_request import (
    ItemPublicTokenExchangeRequest,
)
from plaid.model.link_token_create_request import LinkTokenCreateRequest
from plaid.model.link_token_create_request_user import LinkTokenCreateRequestUser
from plaid.model.products import Products
from plaid.model.transactions_get_request import TransactionsGetRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions

from odoo import _, models
from odoo.exceptions import ValidationError


class PlaidInterface(models.AbstractModel):
    _name = "plaid.interface"
    _description = "Plaid Interface"

    def _get_host(self, host):
        if host == "development":
            return plaid.Environment.Development
        if host == "sandbox":
            return plaid.Environment.Sandbox
        if host == "production":
            return plaid.Environment.Production
        return False

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
            raise ValidationError(_("Error getting client api: %s") % e.body) from e

    def _link(self, client, language, country_code, company_name, products):
        request = LinkTokenCreateRequest(
            products=[Products(product) for product in products],
            client_name=company_name,
            country_codes=[CountryCode(country_code)],
            language=language,
            user=LinkTokenCreateRequestUser(client_user_id="client"),
        )
        try:
            response = client.link_token_create(request)
        except plaid.ApiException as e:
            raise ValidationError(_("Error getting link token: %s") % e.body) from e
        return response.to_dict()["link_token"]

    def _login(self, client, public_token):
        request = ItemPublicTokenExchangeRequest(public_token=public_token)
        try:
            response = client.item_public_token_exchange(request)
        except plaid.ApiException as e:
            raise ValidationError(_("Error getting access token: %s") % e.body) from e
        return response["access_token"]

    def _get_transactions(self, client, access_token, start_date, end_date):
        request = TransactionsGetRequest(
            access_token=access_token,
            start_date=start_date.date(),
            end_date=end_date.date(),
        )
        try:
            response = client.transactions_get(request)
        except plaid.ApiException as e:
            raise ValidationError(_("Error getting transactions: %s") % e.body) from e
        transactions = response["transactions"]
        while len(transactions) < response["total_transactions"]:
            options = TransactionsGetRequestOptions()
            options.offset = len(transactions)
            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=start_date.date(),
                end_date=end_date.date(),
                options=options,
            )
            try:
                response = client.transactions_get(request)
            except plaid.ApiException as e:
                raise ValidationError(
                    _("Error getting transactions: %s") % e.body
                ) from e
            transactions.extend(response["transactions"])
        return transactions
