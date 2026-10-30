# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import logging
import re
import urllib.request
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import urlencode

import pytz

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html2plaintext

_logger = logging.getLogger(__name__)

STRIPE_API_BASE = "https://api.stripe.com/v1"


class OnlineBankStatementProviderStripe(models.Model):
    _inherit = "online.bank.statement.provider"

    stripe_label = fields.Char(
        default=(
            "stripe {source.metadata.invoice_number} {source.object} "
            "{source.id} {source.payment_method_details.type}"
        )
    )
    stripe_note = fields.Char()
    stripe_reference = fields.Char(default="{source.metadata.invoice_number}")
    stripe_fee_label = fields.Char(
        default=(
            "stripe fee {source.metadata.invoice_number} {source.object} "
            "{source.id} {source.payment_method_details.type}"
        )
    )
    stripe_fee_note = fields.Char()
    stripe_fee_reference = fields.Char()
    stripe_expand = fields.Char(default="data.source")
    stripe_foreign_currency = fields.Boolean(
        string="Payments in Foreign Currencies",
        help="For the payments made in a currency other than the one of the "
        "balance, keep on the line the amount and the currency of the payment.",
    )

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("stripe", "Stripe"),
        ]

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "stripe":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover
        currency = self.currency_id or self.company_id.currency_id
        if date_since.tzinfo:
            date_since = date_since.astimezone(pytz.utc).replace(tzinfo=None)
        if date_until.tzinfo:
            date_until = date_until.astimezone(pytz.utc).replace(tzinfo=None)
        date_since = int(date_since.timestamp())
        date_until = int(date_until.timestamp())
        params = [
            ("created[gte]", date_since),
            ("created[lt]", date_until),
        ]
        for s in self.stripe_expand.split(","):
            s = s.strip()
            if not s:
                continue
            params.append(("expand[]", s))
        lines = []
        other_currencies = set()
        for tx in self._stripe_api_get_all("/balance_transactions", params):
            if tx["currency"].lower() != currency.name.lower():
                other_currencies.add(tx["currency"].upper())
                continue
            lines.append(
                {
                    "ref": safe_format(self.stripe_reference, tx),
                    "payment_ref": safe_format(self.stripe_label, tx),
                    "narration": safe_format(self.stripe_note, tx),
                    "amount": float(tx["amount"]) / (10**currency.decimal_places),
                    "date": datetime.fromtimestamp(tx["created"]),
                    "unique_import_id": tx["id"],
                    "raw_data": json.dumps(tx),
                    **self._stripe_foreign_currency_values(tx),
                }
            )
            if tx.get("fee"):
                lines.append(
                    {
                        "ref": safe_format(self.stripe_fee_reference, tx),
                        "payment_ref": safe_format(self.stripe_fee_label, tx),
                        "narration": safe_format(self.stripe_fee_note, tx),
                        "amount": float(-tx["fee"]) / (10**currency.decimal_places),
                        "date": datetime.fromtimestamp(tx["created"]),
                        "unique_import_id": tx["id"] + "_fee",
                        "raw_data": json.dumps(tx),
                    }
                )
        if other_currencies:
            self._stripe_warn_other_currencies(other_currencies)
        return lines, {}

    def _stripe_foreign_currency_values(self, tx):
        """Amount and currency of a payment made in another currency"""
        self.ensure_one()
        source = tx.get("source")
        if not self.stripe_foreign_currency or not isinstance(source, dict):
            return {}
        source_currency = (source.get("currency") or "").upper()
        if not source_currency or source_currency == tx["currency"].upper():
            return {}
        foreign_currency = (
            self.env["res.currency"]
            .with_context(active_test=False)
            .search([("name", "=", source_currency)], limit=1)
        )
        # A charge may be captured only in part
        amount = source.get("amount_captured") or source.get("amount")
        if not foreign_currency or not amount or not tx.get("amount"):
            return {}
        sign = -1 if tx["amount"] < 0 else 1
        return {
            "foreign_currency_id": foreign_currency.id,
            "amount_currency": sign
            * abs(amount)
            / (10**foreign_currency.decimal_places),
        }

    def _stripe_warn_other_currencies(self, currencies):
        """Warn about the transactions of the balances in other currencies.

        They belong to another balance of the Stripe account, which needs a
        provider on a journal in that currency: no warning when it exists.
        """
        self.ensure_one()
        handled = self.search(
            [
                ("service", "=", "stripe"),
                ("password", "=", self.password),
                ("id", "!=", self.id),
            ]
        ).mapped(
            lambda provider: (
                provider.currency_id or provider.company_id.currency_id
            ).name
        )
        missing = sorted(currencies - set(handled))
        if not missing:
            return
        message = _(
            "Transactions in %(currencies)s were not imported, because they "
            "belong to the balance of the Stripe account in that currency. To "
            "import them, add a provider with the same key on a journal in that "
            "currency.",
            currencies=", ".join(missing),
        )
        _logger.warning("Stripe provider %s: %s", self.name, message)
        # Once, not at each pull
        last_message = self.message_ids[:1]
        if not last_message or html2plaintext(last_message.body) != message:
            self.message_post(body=message)

    @api.model
    def _stripe_api_get_all(self, path, params=None):
        if params is None:
            params = []
        starting_after = None
        while True:
            call_params = [*params]
            if starting_after:
                call_params.append(("starting_after", starting_after))
            j = self._stripe_api_get(path, params=call_params)
            yield from j["data"]
            if j["has_more"]:
                starting_after = j["data"][-1]["id"]
            else:
                break

    @api.model
    def _stripe_api_get(self, path, params=None, data=None):
        if params is None:
            params = {}
        try:
            request = urllib.request.Request(
                (self.api_base or STRIPE_API_BASE) + path + "?" + urlencode(params),
                data=data,
            )
            request.add_header("Authorization", f"Bearer {self.password}")
            response = urllib.request.urlopen(request)
            content = response.read().decode("utf-8")
            return json.loads(content)
        except HTTPError as e:
            content = json.loads(e.read().decode("utf-8"))
            raise UserError(f"Stripe API call failed: {path}: {content}") from e


def safe_format(template, kwargs):
    template = template or ""

    def sub(m: re.Match):
        val = kwargs
        for k in m.group(1).split("."):
            try:
                val = val[k]
            except (KeyError, TypeError):
                val = None
        if val is None:
            return ""
        return str(val)

    return re.sub(r"\{([^}]+)\}", sub, template)
