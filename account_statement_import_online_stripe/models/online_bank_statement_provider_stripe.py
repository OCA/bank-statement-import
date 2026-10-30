# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
import re
import urllib.request
from datetime import datetime
from urllib.error import HTTPError
from urllib.parse import urlencode

import pytz

from odoo import api, fields, models
from odoo.exceptions import UserError

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
    stripe_statement_balances = fields.Boolean(
        string="Statement Balances",
        help="Set the starting and ending balances of the statements from the "
        "balance of the Stripe account, so that Odoo shows the statements whose "
        "lines do not match it. It needs more requests to Stripe.",
    )

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("stripe", "Stripe"),
        ]

    def _pull(self, date_since, date_until):
        # The balance of the account and its later transactions are read from
        # Stripe once per pull, and used for all its periods.
        if "stripe_balance_cache" not in self.env.context:
            self = self.with_context(stripe_balance_cache={})
        return super()._pull(date_since, date_until)

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
        transactions = list(self._stripe_api_get_all("/balance_transactions", params))
        for tx in transactions:
            if tx["currency"].lower() != currency.name.lower():
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
        statement_values = {}
        if self.stripe_statement_balances:
            factor = 10**currency.decimal_places
            balance_end = self._stripe_balance_at(date_until, currency)
            period_net = sum(
                tx.get("net", 0)
                for tx in transactions
                if tx["currency"].lower() == currency.name.lower()
            )
            statement_values = {
                "balance_start": (balance_end - period_net) / factor,
                "balance_end_real": balance_end / factor,
            }
        return lines, statement_values

    def _stripe_balance_at(self, timestamp, currency):
        """Balance of the Stripe account at a time, in the smallest unit.

        It is the current balance (available and pending) less the net amounts
        of the transactions created since then.
        """
        self.ensure_one()
        cache = self.env.context.get("stripe_balance_cache")
        if cache is None:
            cache = {}
        entry = cache.get(self.id)
        if not entry or entry["since"] > timestamp:
            later = [
                (tx["created"], tx.get("net", 0))
                for tx in self._stripe_api_get_all(
                    "/balance_transactions", [("created[gte]", timestamp)]
                )
                if tx["currency"].lower() == currency.name.lower()
            ]
            balance = self._stripe_api_get("/balance")
            current = sum(
                amount["amount"]
                for amount in balance.get("available", []) + balance.get("pending", [])
                if amount["currency"].lower() == currency.name.lower()
            )
            entry = cache[self.id] = {
                "since": timestamp,
                "current": current,
                "later": later,
            }
        return entry["current"] - sum(
            net for created, net in entry["later"] if created >= timestamp
        )

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
