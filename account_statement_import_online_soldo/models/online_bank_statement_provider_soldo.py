# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import hashlib
import json
import logging
from datetime import datetime, timedelta

import pytz
import requests
from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from markupsafe import Markup

from odoo import api, fields, models
from odoo.exceptions import UserError
from odoo.tools import float_compare, format_datetime, plaintext2html

_logger = logging.getLogger(__name__)

SOLDO_API_BASE = "https://api.soldo.com"
SOLDO_TRANSACTIONS_PATH = "/business/v2/transactions"
SOLDO_PAGE_SIZE = 50
SOLDO_TIMEOUT = 60
# Soldo refuses longer intervals with INTERVAL_TO_LARGE
SOLDO_MAX_INTERVAL_DAYS = 29
# Order in which Soldo concatenates the parameters of a transaction search to
# compute the fingerprint; the fingerprint token always comes last.
SOLDO_SEARCH_FINGERPRINT_ORDER = ("fromDate", "toDate", "dateType")
SOLDO_ATTACHMENTS_PATH = "/business/v2/transactions/%s/attachments"
SOLDO_ATTACHMENT_MAX_SIZE = 25 * 1024 * 1024
# Description of the imported attachments, followed by the Soldo attachment id:
# it tells the files already imported from the ones added later in Soldo
SOLDO_ATTACHMENT_PREFIX = "Soldo attachment "
SOLDO_SETTLED = "Settled"
SOLDO_AUTHORISED = "Authorised"


class OnlineBankStatementProviderSoldo(models.Model):
    _inherit = "online.bank.statement.provider"

    soldo_import_state = fields.Selection(
        selection=[
            ("settled", "Settled transactions"),
            ("authorised", "Authorised and settled transactions"),
        ],
        string="Soldo Transactions",
        default="settled",
        help="Settled: the transactions are imported once settled, on their "
        "settlement date and with their final amount.\n"
        "Authorised and settled: the transactions are imported as soon as they "
        "are authorised, on their transaction date. The amount of an "
        "authorisation can still change when it is settled, and an "
        "authorisation can be cancelled after the import.",
    )
    soldo_settlement_days = fields.Integer(
        default=10,
        help="How many days before the period the settled transactions are "
        "searched for: a card payment is settled some days after it is made.",
    )
    soldo_excluded_wallets = fields.Char(
        help="Comma separated names or ids of the wallets whose transactions "
        "are not imported, for instance the company wallet that tops up the "
        "cards.",
    )
    soldo_private_key = fields.Text(
        compute="_compute_soldo_private_key",
        inverse="_inverse_soldo_private_key",
        groups="base.group_system",
        help="The private key, in PEM format, whose public key is registered in "
        "Soldo. Once saved it is not shown again: paste a new key to replace it.",
    )
    soldo_private_key_set = fields.Boolean(
        compute="_compute_soldo_private_key",
        groups="base.group_system",
    )
    soldo_attachments = fields.Boolean(
        string="Import Soldo Attachments",
        help="Download the receipts and invoices attached to the transactions "
        "in Soldo and attach them to the journal entries of the statement lines, "
        "also when they are attached in Soldo after the import.",
    )
    soldo_update_lines = fields.Boolean(
        string="Update Imported Soldo Transactions",
        help="Search the transactions changed in Soldo during the period and "
        "update the statement lines already imported. The label and the "
        "amount are updated only while the line is not reconciled: a "
        "reconciled line whose amount changed, and a line whose transaction "
        "was cancelled, are reported on the provider.",
    )

    @api.depends("certificate_private_key")
    def _compute_soldo_private_key(self):
        for provider in self:
            provider.soldo_private_key = False
            provider.soldo_private_key_set = bool(provider.certificate_private_key)

    def _inverse_soldo_private_key(self):
        for provider in self:
            if provider.soldo_private_key:
                provider.certificate_private_key = provider.soldo_private_key

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("soldo", "Soldo"),
        ]

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "soldo":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover
        date_since = _soldo_naive_utc(date_since)
        date_until = _soldo_naive_utc(date_until)
        if self.soldo_import_state == "settled":
            # The line takes the settlement date, which comes after the date of
            # the transaction searched for
            date_since -= timedelta(days=max(self.soldo_settlement_days, 0))
        currency = (self.currency_id or self.company_id.currency_id).name
        excluded_wallets = self._soldo_excluded_wallets()
        token = self._soldo_get_access_token()
        lines = []
        for transaction in self._soldo_get_transactions(token, date_since, date_until):
            if self._soldo_is_importable(transaction, excluded_wallets, currency):
                lines += self._soldo_transaction_to_lines(transaction)
        return lines, {}

    def _soldo_excluded_wallets(self):
        return {
            wallet.strip()
            for wallet in (self.soldo_excluded_wallets or "").split(",")
            if wallet.strip()
        }

    def _soldo_is_importable(self, transaction, excluded_wallets, currency):
        states = {SOLDO_SETTLED}
        if self.soldo_import_state == "authorised":
            states.add(SOLDO_AUTHORISED)
        if transaction.get("status") not in states:
            return False
        wallets = {transaction.get("wallet_name"), transaction.get("wallet_id")}
        if excluded_wallets & wallets:
            return False
        transaction_currency = transaction.get("amount_currency")
        return not transaction_currency or transaction_currency == currency

    def _soldo_transaction_date(self, transaction):
        date = transaction.get("date")
        if self.soldo_import_state == "settled":
            date = transaction.get("settlement_date") or date
        return _soldo_parse_date(date)

    def _soldo_transaction_to_lines(self, transaction):
        date = self._soldo_transaction_date(transaction)
        sign = -1 if transaction.get("transaction_sign") == "Negative" else 1
        merchant = transaction.get("merchant") or {}
        label = merchant.get("name") or transaction.get("category") or transaction["id"]
        line = {
            "date": date,
            "amount": sign * float(transaction.get("amount") or 0.0),
            "payment_ref": label,
            "ref": transaction.get("tx_id") or transaction["id"],
            "partner_name": merchant.get("name") or False,
            "transaction_type": transaction.get("category") or False,
            "narration": self._soldo_notes(transaction),
            "unique_import_id": transaction["id"],
            "raw_data": json.dumps(transaction),
        }
        line.update(self._soldo_foreign_currency_values(transaction, sign))
        lines = [line]
        fee = float(transaction.get("fee_amount") or 0.0)
        fee_currency = transaction.get("fee_currency")
        if fee and fee_currency in (None, transaction.get("amount_currency")):
            lines.append(
                {
                    "date": date,
                    "amount": -abs(fee),
                    "payment_ref": self.env._("Soldo fee: %(label)s", label=label),
                    "ref": line["ref"],
                    "partner_name": "Soldo",
                    "transaction_type": "fee",
                    "unique_import_id": f"{transaction['id']}-FEE",
                    "raw_data": line["raw_data"],
                }
            )
        return lines

    def _soldo_notes(self, transaction):
        """Notes of the transaction and notes of the card user, if any."""
        notes = [
            transaction[key].strip()
            for key in ("notes", "user_notes")
            if (transaction.get(key) or "").strip()
        ]
        return plaintext2html("\n".join(notes)) if notes else False

    def _create_or_update_statement(
        self, data, statement_date_since, statement_date_until
    ):
        if self.service != "soldo":
            return super()._create_or_update_statement(
                data, statement_date_since, statement_date_until
            )
        StatementLine = self.env["account.bank.statement.line"]
        unique_import_ids = self._soldo_unique_import_ids(
            self._soldo_transaction_ids(data)
        )
        domain = [("unique_import_id", "in", list(unique_import_ids))]
        existing_lines = StatementLine.search(domain)
        statement = super()._create_or_update_statement(
            data, statement_date_since, statement_date_until
        )
        new_lines = StatementLine.search(domain) - existing_lines
        self._soldo_post_details(new_lines)
        if self.soldo_attachments or self.soldo_update_lines:
            try:
                self._soldo_import_changes(
                    new_lines, statement_date_since, statement_date_until
                )
            except UserError as error:
                if not self.env.context.get("scheduled"):
                    raise
                self._log_provider_exception(
                    error, statement_date_since, statement_date_until
                )
        return statement

    def _soldo_import_changes(self, new_lines, date_since, date_until):
        """Search once the transactions changed in Soldo during the period, then
        import their files and update their lines, as the options ask."""
        token = self._soldo_get_access_token()
        updated_transactions = {
            transaction["id"]: transaction
            for transaction in self._soldo_get_transactions(
                token,
                _soldo_naive_utc(date_since),
                _soldo_naive_utc(date_until),
                date_type="UPDATE",
            )
        }
        if self.soldo_attachments:
            self._soldo_import_attachments(token, new_lines, updated_transactions)
        if self.soldo_update_lines:
            self._soldo_update_statement_lines(updated_transactions)

    def _soldo_import_attachments(self, token, new_lines, updated_transactions):
        """Attach the files of the new lines, and the files attached in Soldo to
        the lines imported before."""
        # Files are often attached days after the payment: attaching them
        # changes the transaction, found among the ones updated in the period
        updated_ids = self._soldo_unique_import_ids(
            transaction_id
            for transaction_id, transaction in updated_transactions.items()
            if transaction.get("has_attachments")
        )
        updated_lines = self.env["account.bank.statement.line"].search(
            [("unique_import_id", "in", list(updated_ids))]
        )
        new_lines = new_lines.filtered(
            lambda line: json.loads(line.raw_data or "{}").get("has_attachments")
        )
        self._soldo_sync_attachments(token, new_lines | updated_lines)

    def _soldo_sync_attachments(self, token, statement_lines):
        """Attach the files of the transactions that the journal entries of the
        statement lines do not have yet. A failed download does not stop the
        import: it is logged and reported on the provider."""
        failures = []
        Attachment = self.env["ir.attachment"]
        for statement_line in statement_lines:
            transaction_id = json.loads(statement_line.raw_data or "{}").get("id")
            if not transaction_id:
                continue
            try:
                attachments = self._soldo_get_attachments(token, transaction_id)
            except UserError as error:
                failures.append((transaction_id, error))
                continue
            imported = set(
                Attachment.search(
                    [
                        ("res_model", "=", "account.move"),
                        ("res_id", "=", statement_line.move_id.id),
                        ("description", "=like", f"{SOLDO_ATTACHMENT_PREFIX}%"),
                    ]
                ).mapped("description")
            )
            values = []
            for attachment in attachments:
                key = SOLDO_ATTACHMENT_PREFIX + (
                    attachment.get("attachment_id") or attachment.get("file_name") or ""
                )
                if key in imported:
                    continue
                try:
                    content = self._soldo_download(attachment)
                except UserError as error:
                    failures.append((transaction_id, error))
                    continue
                values.append(
                    {
                        "name": attachment.get("file_name")
                        or attachment.get("attachment_id"),
                        "raw": content,
                        "res_model": "account.move",
                        "res_id": statement_line.move_id.id,
                        "description": key,
                    }
                )
            Attachment.create(values)
        for transaction_id, error in failures:
            _logger.warning(
                "Soldo attachment of transaction %s not imported: %s",
                transaction_id,
                error,
            )
        if failures:
            self.message_post(
                body=self.env._(
                    "Some attachments were not imported from Soldo: %(failures)s",
                    failures="; ".join(
                        f"{transaction_id}: {error}"
                        for transaction_id, error in failures
                    ),
                )
            )

    def _soldo_get_attachments(self, token, transaction_id):
        """Attachments of a transaction, with the links to their files. The
        request needs the token only, not the signature."""
        headers = {"Authorization": f"Bearer {token}"}
        data = self._soldo_request(
            "get", SOLDO_ATTACHMENTS_PATH % transaction_id, headers=headers
        )
        return data.get("attachments") or []

    def _soldo_download(self, attachment):
        """Content of the file of an attachment."""
        too_large = UserError(
            self.env._(
                "%(name)s is larger than the size allowed for an attachment.",
                name=attachment.get("file_name") or attachment.get("attachment_id"),
            )
        )
        if (attachment.get("file_size") or 0) > SOLDO_ATTACHMENT_MAX_SIZE:
            raise too_large
        try:
            response = requests.get(attachment.get("url"), timeout=SOLDO_TIMEOUT)
            response.raise_for_status()
        except requests.RequestException as error:
            raise UserError(
                self.env._("Soldo attachment download failed: %(error)s", error=error)
            ) from error
        if len(response.content) > SOLDO_ATTACHMENT_MAX_SIZE:
            raise too_large
        return response.content

    def _soldo_update_statement_lines(self, transactions):
        """Update the statement lines of the transactions changed in Soldo
        during the period."""
        unique_import_ids = self._soldo_unique_import_ids(transactions)
        statement_lines = self.env["account.bank.statement.line"].search(
            [("unique_import_id", "in", list(unique_import_ids))]
        )
        currency = (self.currency_id or self.company_id.currency_id).name
        excluded_wallets = self._soldo_excluded_wallets()
        warnings = []
        for statement_line in statement_lines:
            transaction = transactions[
                unique_import_ids[statement_line.unique_import_id]
            ]
            if json.loads(statement_line.raw_data or "{}") == transaction:
                continue
            if not self._soldo_is_importable(transaction, excluded_wallets, currency):
                warnings.append(
                    self.env._(
                        "%(line)s: the transaction is now %(status)s.",
                        line=statement_line.display_name,
                        status=transaction.get("status"),
                    )
                )
                continue
            warning = self._soldo_update_statement_line(statement_line, transaction)
            if warning:
                warnings.append(warning)
        if warnings:
            self.message_post(
                body=self.env._(
                    "Some statement lines could not be updated from Soldo: "
                    "%(warnings)s",
                    warnings=" ".join(warnings),
                )
            )

    def _soldo_update_statement_line(self, statement_line, transaction):
        """Write the new values of the transaction on its statement line, and log
        them in the chatter of its journal entry when the details shown there
        change: Soldo also changes a transaction for internal values only, for
        instance when a file is attached.

        The label, the amounts and the partner of a reconciled line are kept:
        changing them would rewrite its journal entry.
        """
        provider = self._soldo_details_provider()
        old_details = provider._soldo_details_body(
            statement_line, json.loads(statement_line.raw_data or "{}")
        )
        line = self._soldo_transaction_to_lines(transaction)[0]
        values = {
            key: line.get(key) or False
            for key in ("ref", "partner_name", "transaction_type", "narration")
        }
        values["raw_data"] = line["raw_data"]
        accounting_values = {
            "payment_ref": line["payment_ref"],
            "amount": line["amount"],
            "foreign_currency_id": line.get("foreign_currency_id", False),
            "amount_currency": line.get("amount_currency", 0.0),
        }
        warning = False
        if not statement_line.is_reconciled:
            values.update(accounting_values)
        elif float_compare(
            statement_line.amount,
            line["amount"],
            precision_rounding=statement_line.currency_id.rounding,
        ):
            warning = self.env._(
                "%(line)s: the amount is now %(amount)s, but the line is reconciled.",
                line=statement_line.display_name,
                amount=line["amount"],
            )
        statement_line.write(values)
        if provider._soldo_details_body(statement_line, transaction) != old_details:
            provider._soldo_post_details(
                statement_line, title=provider.env._("Soldo transaction updated")
            )
        return warning

    def _soldo_transaction_ids(self, data):
        """Ids of the transactions of the lines, without their fee lines."""
        transaction_ids = []
        for line in (data or ([], {}))[0] or []:
            transaction = json.loads(line.get("raw_data") or "{}")
            # The fee line has the raw data of its transaction too
            if line.get("unique_import_id") == transaction.get("id"):
                transaction_ids.append(transaction["id"])
        return transaction_ids

    def _soldo_unique_import_ids(self, transaction_ids):
        """Unique import ids that the journal gives to the statement lines of
        the transactions, mapped to the transaction ids."""
        unique_import_ids = {}
        for transaction_id in transaction_ids:
            values = {"unique_import_id": transaction_id}
            self.journal_id._statement_line_import_update_unique_import_id(
                values, self.account_number
            )
            unique_import_ids[values["unique_import_id"]] = transaction_id
        return unique_import_ids

    def _soldo_post_details(self, statement_lines, title=None):
        """Log the details of the Soldo transactions in the chatter of the
        journal entries of the statement lines."""
        provider = self._soldo_details_provider()
        for statement_line in statement_lines:
            transaction = json.loads(statement_line.raw_data or "{}")
            statement_line.move_id._message_log(
                body=provider._soldo_details_body(statement_line, transaction, title)
            )

    def _soldo_details_provider(self):
        """The details are logged once for all the readers: in the language and
        time zone of the company, not of the user who runs the import, often a
        scheduled action."""
        partner = self.company_id.partner_id
        return self.with_context(
            lang=partner.lang or self.env.lang,
            tz=partner.tz or self.env.context.get("tz"),
        )

    def _soldo_details(self, statement_line, transaction):
        """Label and value of the details of a transaction shown in the chatter;
        empty values are left out."""
        merchant_category = transaction.get("merchant_category") or {}
        card = transaction.get("wallet_name") or ""
        if transaction.get("masked_pan"):
            card = f"{card} ({transaction['masked_pan']})".strip()
        original_amount = False
        if transaction.get("tx_amount_currency") not in (
            None,
            transaction.get("amount_currency"),
        ):
            original_amount = (
                f"{transaction.get('tx_amount')} {transaction['tx_amount_currency']}"
            )
        fee = False
        if transaction.get("fee_amount"):
            fee = f"{transaction['fee_amount']} {transaction.get('fee_currency') or ''}"
        link = False
        if transaction.get("direct_url"):
            link = Markup('<a href="%s" target="_blank">%s</a>') % (
                transaction["direct_url"],
                self.env._("Open in Soldo"),
            )
        return [
            (self.env._("Card"), card),
            (self.env._("Merchant"), (transaction.get("merchant") or {}).get("name")),
            (
                self.env._("Merchant category"),
                " - ".join(
                    str(value)
                    for value in (
                        merchant_category.get("mcc"),
                        merchant_category.get("mcc_description"),
                    )
                    if value
                ),
            ),
            (
                self.env._("Expense category"),
                (transaction.get("expense_category") or {}).get("name"),
            ),
            (self.env._("Notes"), transaction.get("notes")),
            (self.env._("User notes"), transaction.get("user_notes")),
            (self.env._("Type"), transaction.get("category")),
            (self.env._("Status"), transaction.get("status")),
            (
                self.env._("Transaction date"),
                self._soldo_format_datetime(transaction.get("date")),
            ),
            (
                self.env._("Settlement date"),
                self._soldo_format_datetime(transaction.get("settlement_date")),
            ),
            (self.env._("Original amount"), original_amount),
            (self.env._("Fee"), fee),
            (self.env._("Transaction"), transaction.get("tx_id")),
            (self.env._("Link"), link),
        ]

    def _soldo_details_body(self, statement_line, transaction, title=None):
        items = Markup("").join(
            Markup("<li><b>%s</b>: %s</li>") % (label, value)
            for label, value in self._soldo_details(statement_line, transaction)
            if value
        )
        return Markup("<p><b>%s</b></p><ul>%s</ul>") % (
            title or self.env._("Soldo transaction"),
            items,
        )

    def _soldo_format_datetime(self, value):
        if not value:
            return False
        return format_datetime(
            self.env, _soldo_parse_date(value), tz=self.env.context.get("tz")
        )

    def _soldo_foreign_currency_values(self, transaction, sign):
        """Amount in the currency of the payment, when it is not the one of the
        wallet."""
        code = transaction.get("tx_amount_currency")
        if not code or code == transaction.get("amount_currency"):
            return {}
        currency = (
            self.env["res.currency"]
            .with_context(active_test=False)
            .search([("name", "=", code)], limit=1)
        )
        if not currency:
            return {}
        return {
            "foreign_currency_id": currency.id,
            "amount_currency": sign * float(transaction.get("tx_amount") or 0.0),
        }

    def _soldo_get_transactions(self, token, date_since, date_until, date_type=None):
        """Transactions of the period, searched in intervals Soldo accepts.

        With the date type UPDATE, the transactions changed during the period.

        The bounds go as UTC date times: with dates only, Soldo leaves out the
        transactions of the day passed as bound. A transaction on the border of
        two intervals is returned once.
        """
        seen = set()
        start = date_since
        while start < date_until:
            end = min(start + timedelta(days=SOLDO_MAX_INTERVAL_DAYS), date_until)
            params = {
                "fromDate": _soldo_format_date(start),
                "toDate": _soldo_format_date(end),
            }
            if date_type:
                params["dateType"] = date_type
            for transaction in self._soldo_search(
                token, SOLDO_TRANSACTIONS_PATH, params
            ):
                if transaction["id"] not in seen:
                    seen.add(transaction["id"])
                    yield transaction
            start = end

    def _soldo_search(self, token, path, params):
        values = [
            params[key] for key in SOLDO_SEARCH_FINGERPRINT_ORDER if params.get(key)
        ]
        headers = self._soldo_fingerprint_headers(token, values)
        page = 0
        while True:
            data = self._soldo_request(
                "get",
                path,
                params=dict(params, p=page, s=SOLDO_PAGE_SIZE),
                headers=headers,
            )
            yield from data.get("results") or []
            page += 1
            if page >= (data.get("pages") or 0):
                break

    def _soldo_get_access_token(self):
        data = self._soldo_request(
            "post",
            "/oauth/authorize",
            data={"client_id": self.username, "client_secret": self.password},
        )
        return data["access_token"]

    def _soldo_fingerprint_headers(self, token, values):
        """Headers of the advanced authentication of Soldo.

        The fingerprint is the SHA-512 of the values of the request followed by
        the fingerprint token, signed with SHA512withRSA by the private key whose
        public key is registered in Soldo.
        """
        fingerprint_value = "".join(values) + (self.passphrase or "")
        fingerprint = hashlib.sha512(fingerprint_value.encode()).hexdigest()
        try:
            private_key = serialization.load_pem_private_key(
                (self.certificate_private_key or "").encode(), password=None
            )
            signature = private_key.sign(
                fingerprint.encode(), padding.PKCS1v15(), hashes.SHA512()
            )
        except (TypeError, ValueError, UnsupportedAlgorithm) as error:
            raise UserError(
                self.env._(
                    "The private key of %(provider)s is not a valid RSA key "
                    "in PEM format.",
                    provider=self.name,
                )
            ) from error
        return {
            "Authorization": f"Bearer {token}",
            "X-Soldo-Fingerprint": fingerprint,
            "X-Soldo-Fingerprint-Signature": base64.b64encode(signature).decode(),
        }

    def _soldo_request(self, method, path, **kwargs):
        url = (self.api_base or SOLDO_API_BASE).rstrip("/") + path
        headers = dict(kwargs.pop("headers", None) or {}, Accept="application/json")
        try:
            response = requests.request(
                method, url, headers=headers, timeout=SOLDO_TIMEOUT, **kwargs
            )
        except requests.RequestException as error:
            raise UserError(
                self.env._(
                    "Soldo API call failed: %(path)s: %(error)s",
                    path=path,
                    error=error,
                )
            ) from error
        try:
            content = response.json()
        except ValueError:
            content = {}
        if not response.ok:
            message = (
                content.get("message")
                or content.get("error_description")
                or response.text
            )
            raise UserError(
                self.env._(
                    "Soldo API call failed: %(path)s: %(status)s %(message)s",
                    path=path,
                    status=response.status_code,
                    message=message,
                )
            )
        return content


def _soldo_naive_utc(date):
    if date.tzinfo:
        date = date.astimezone(pytz.utc).replace(tzinfo=None)
    return date


def _soldo_parse_date(value):
    """Soldo dates, like 2017-06-01T12:48:40Z, as naive UTC datetimes."""
    return _soldo_naive_utc(datetime.fromisoformat(value.replace("Z", "+00:00")))


def _soldo_format_date(date):
    """Naive UTC datetimes as search bounds, like 2017-06-01T12:48:40Z."""
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")
