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
        for tx in self._stripe_api_get_all("/balance_transactions", params):
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
                    "raw_data": tx,
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
                        "raw_data": tx,
                    }
                )
        return lines, {}

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
            request.add_header("Authorization", "Bearer %s" % self.password)
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
