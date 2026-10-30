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
    stripe_skip_website_payments = fields.Boolean(
        string="Payments Already Recorded by Odoo",
        help="Payments made through the Stripe payment provider of Odoo (for "
        "instance on the website) are already recorded by Odoo. When their "
        "payment is posted on the account of this journal, the line of the "
        "payment is not imported again (its fee is); otherwise the line gets the "
        "partner of the payment, ready to be reconciled. It needs the Payment "
        "module.",
    )
    stripe_payment_installed = fields.Boolean(
        compute="_compute_stripe_payment_installed"
    )

    def _compute_stripe_payment_installed(self):
        installed = "payment.transaction" in self.env
        for provider in self:
            provider.stripe_payment_installed = installed

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
        transactions = list(self._stripe_api_get_all("/balance_transactions", params))
        odoo_payments = {}
        if self.stripe_skip_website_payments:
            odoo_payments = self._stripe_get_odoo_payments(transactions)
        for tx in transactions:
            if tx["currency"].lower() != currency.name.lower():
                continue
            payment_values = {}
            odoo_payment = next(
                (
                    odoo_payments[key]
                    for key in _stripe_payment_keys(tx)
                    if key in odoo_payments
                ),
                None,
            )
            if odoo_payment:
                payment_values = self._stripe_odoo_payment_line_values(odoo_payment)
            if payment_values is not None:
                lines.append(
                    {
                        "ref": safe_format(self.stripe_reference, tx),
                        "payment_ref": safe_format(self.stripe_label, tx),
                        "narration": safe_format(self.stripe_note, tx),
                        "amount": float(tx["amount"]) / (10**currency.decimal_places),
                        "date": datetime.fromtimestamp(tx["created"]),
                        "unique_import_id": tx["id"],
                        "raw_data": json.dumps(tx),
                        **payment_values,
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
        return lines, {}

    def _stripe_get_odoo_payments(self, transactions):
        """Payments recorded by the Stripe payment provider of Odoo.

        :return: a dict mapping the Stripe ids of the payments (payment intent,
            charge or refund) to their ``payment.transaction``
        """
        self.ensure_one()
        if "payment.transaction" not in self.env:
            return {}
        keys = set()
        for tx in transactions:
            keys.update(_stripe_payment_keys(tx))
        if not keys:
            return {}
        payment_transactions = (
            self.env["payment.transaction"]
            .sudo()
            .search(
                [
                    ("provider_code", "=", "stripe"),
                    ("provider_reference", "in", list(keys)),
                    ("state", "=", "done"),
                ]
            )
        )
        return {ptx.provider_reference: ptx for ptx in payment_transactions}

    def _stripe_odoo_payment_line_values(self, payment_transaction):
        """Values of the line of a payment already recorded by Odoo.

        :return: None when the payment is already posted on the account of the
            journal, so that the line must not be imported again; otherwise the
            values to add to the line
        """
        self.ensure_one()
        payment = (
            payment_transaction.payment_id
            if "payment_id" in payment_transaction._fields
            else None
        )
        if (
            payment
            and payment.move_id.state == "posted"
            and payment.outstanding_account_id
            and payment.outstanding_account_id == self.journal_id.default_account_id
        ):
            return None
        return {"partner_id": payment_transaction.partner_id.id}

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


def _stripe_payment_keys(tx):
    """Stripe ids under which Odoo may have recorded the payment of a transaction"""
    source = tx.get("source")
    if not isinstance(source, dict):
        return set()
    keys = {source.get("id")}
    # Odoo records a payment under its payment intent; a refund also refers to
    # the payment intent of the payment it refunds, which is not its own
    if source.get("object") == "charge":
        keys.add(source.get("payment_intent"))
    return {key for key in keys if isinstance(key, str)}


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
