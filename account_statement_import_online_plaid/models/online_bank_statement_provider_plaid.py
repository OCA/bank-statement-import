# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import api, fields, models


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"
    plaid_access_token = fields.Char()
    plaid_host = fields.Selection(
        [
            ("development", "Development"),
            ("sandbox", "Sandbox"),
            ("production", "Production"),
        ],
        default="sandbox",
    )

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "plaid":
            return super()._obtain_statement_data(date_since, date_until)
        return self._plaid_retrieve_data(date_since, date_until), {}

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("plaid", "Plaid.com"),
        ]

    def action_sync_with_plaid(self):
        self.ensure_one()
        plaid_interface = self.env["plaid.interface"]
        args = [self.username, self.password, self.plaid_host]
        client = plaid_interface._client(*args)
        lang = self.env["res.lang"].search([("code", "=", self.env.user.lang)]).iso_code
        company_name = self.env.user.company_id.name
        country_code = self.env.user.company_id.country_id.code
        link_token = plaid_interface._link(
            client=client,
            language=lang,
            country_code=country_code,
            company_name=company_name,
            products=["transactions"],
        )
        return {
            "type": "ir.actions.client",
            "tag": "plaid_login",
            "params": {
                "call_model": "online.bank.statement.provider",
                "call_method": "plaid_create_access_token",
                "token": link_token,
                "object_id": self.id,
            },
            "target": "new",
        }

    def _plaid_retrieve_data(self, date_since, date_until):
        plaid_interface = self.env["plaid.interface"]
        args = [self.username, self.password, self.plaid_host]
        client = plaid_interface._client(*args)
        transactions = plaid_interface._get_transactions(
            client, self.plaid_access_token, date_since, date_until
        )
        return self._prepare_vals_for_statement(transactions)

    @api.model
    def plaid_create_access_token(self, public_token, active_id):
        provider = self.browse(active_id)
        plaid_interface = self.env["plaid.interface"]
        client = plaid_interface._client(
            provider.username, provider.password, provider.plaid_host
        )
        args = [client, public_token]
        provider.plaid_access_token = plaid_interface._login(*args)
        if provider.plaid_access_token:
            return True
        return False

    def _prepare_vals_for_statement(self, transactions):
        return [
            {
                "date": transaction["date"],
                "ref": transaction["name"],
                "payment_ref": transaction["name"],
                "unique_import_id": transaction["transaction_id"],
                "amount": transaction["amount"],
                "raw_data": transaction,
            }
            for transaction in transactions
        ]
