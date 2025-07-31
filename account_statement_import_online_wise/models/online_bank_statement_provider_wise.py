# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020-2021 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import itertools
import json
import logging
import urllib.request
from base64 import b64encode
from decimal import Decimal
from urllib.error import HTTPError

import dateutil.parser
import pytz
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


WISE_API_BASE = "https://api.transferwise.com"


class OnlineBankStatementProviderWise(models.Model):
    _inherit = "online.bank.statement.provider"

    # NOTE: This is needed to workaround possible multiple 'origin' fields
    # present in the same view, resulting in wrong field view configuration
    # if more than one is widget="dynamic_dropdown"
    wise_profile = fields.Char(
        string="Profile",
        related="origin",
        readonly=False,
    )

    @api.model
    def _get_available_services(self):
        result = super()._get_available_services() + [
            ("wise", "Wise.com (TransferWise.com)"),
        ]
        _logger.info("Available services: %s", result)
        return result

    @api.model
    def values_wise_profile(self):
        api_base = self.env.context.get("api_base") or WISE_API_BASE
        api_key = self.env.context.get("api_key")
        if not api_key:
            return []
        try:
            url = api_base + "/v1/profiles"
            data = self._wise_retrieve(url, api_key)
        except BaseException:
            _logger.warning("Unable to get profiles", exc_info=True)
            return []
        return list(
            map(
                lambda entry: (
                    str(entry["id"]),
                    "%s %s (personal)"
                    % (
                        entry["details"]["firstName"],
                        entry["details"]["lastName"],
                    )
                    if entry["type"] == "personal"
                    else entry["details"]["name"],
                ),
                data,
            )
        )

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "wise":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        _logger.debug("Wise: Starting statement data retrieval from %s to %s", date_since, date_until)
        
        api_base = self.api_base or WISE_API_BASE
        api_key = self.password
        private_key = self.certificate_private_key
        if private_key:
            private_key = serialization.load_pem_private_key(
                private_key.encode(),
                password=None,
                backend=default_backend(),
            )
        currency = (self.currency_id or self.company_id.currency_id).name
        
        _logger.debug("Wise: Using API base: %s, Currency: %s, Profile ID: %s", api_base, currency, self.origin)

        if date_since.tzinfo:
            date_since = date_since.astimezone(pytz.utc).replace(tzinfo=None)
        if date_until.tzinfo:
            date_until = date_until.astimezone(pytz.utc).replace(tzinfo=None)

        # Get corresponding balance by currency
        _logger.debug("Wise: Fetching balances for profile %s", self.origin)
        url = api_base + "/v4/profiles/{}/balances?types=STANDARD".format(self.origin)
        data = self._wise_retrieve(url, api_key, private_key)
        if not data:
            _logger.warning("Wise: No balances found")
            return None
        
        # Find balance for the specified currency
        balance = None
        for balance_item in data:
            if balance_item["currency"] == currency:
                balance = balance_item
                break
        
        if not balance:
            _logger.warning("Wise: No balance found for currency %s", currency)
            return None
            
        balance_id = balance["id"]
        _logger.debug("Wise: Using balance ID: %s", balance_id)

        # Notes on /statement endpoint:
        #  - intervalStart <= date < intervalEnd

        # Get starting balance
        _logger.debug("Wise: Fetching starting balance")
        starting_balance_timestamp = date_since.isoformat() + "Z"
        url = api_base + (
            "/v1/profiles/%s/balance-statements/%s/statement.json"
            + "?currency=%s&intervalStart=%s&intervalEnd=%s&type=COMPACT"
        ) % (
            self.origin,
            balance_id,
            currency,
            starting_balance_timestamp,
            starting_balance_timestamp,
        )
        data = self._wise_retrieve(url, api_key, private_key)
        balance_start = data["endOfStatementBalance"]["value"]
        _logger.debug("Wise: Starting balance: %s", balance_start)

        # Get statements, using 469 days (around 1 year 3 month) as step.
        _logger.debug("Wise: Fetching transactions in chunks")
        interval_step = relativedelta(days=469)
        interval_start = date_since
        interval_end = date_until
        transactions = []
        balance_end = None
        chunk_count = 0
        while interval_start < interval_end:
            chunk_count += 1
            chunk_end = min(interval_start + interval_step, interval_end)
            _logger.debug("Wise: Fetching chunk %d from %s to %s", chunk_count, interval_start, chunk_end)
            url = api_base + (
                "/v1/profiles/%s/balance-statements/%s/statement.json"
                + "?currency=%s&intervalStart=%s&intervalEnd=%s&type=COMPACT"
            ) % (
                self.origin,
                balance_id,
                currency,
                interval_start.isoformat() + "Z",
                chunk_end.isoformat() + "Z",
            )
            data = self._wise_retrieve(url, api_key, private_key)
            chunk_transactions = data["transactions"]
            _logger.debug("Wise: Retrieved %d transactions in chunk %d", len(chunk_transactions), chunk_count)
            transactions += chunk_transactions
            balance_end = data["endOfStatementBalance"]["value"]
            interval_start += interval_step
        if balance_end is None:
            raise UserError(_("Ending balance unavailable"))
        
        _logger.debug("Wise: Total transactions retrieved: %d, Ending balance: %s", len(transactions), balance_end)

        # Normalize transactions' date, sort by it, and get lines
        _logger.debug("Wise: Processing transactions into statement lines")
        transactions = map(
            lambda transaction: self._wise_preparse_transaction(transaction),
            transactions,
        )
        lines = list(
            itertools.chain.from_iterable(
                map(
                    lambda x: self._wise_transaction_to_lines(x),
                    sorted(transactions, key=lambda transaction: transaction["date"]),
                )
            )
        )
        
        _logger.debug("Wise: Generated %d statement lines", len(lines))
        return lines, {"balance_start": balance_start, "balance_end_real": balance_end}

    @api.model
    def _wise_preparse_transaction(self, transaction):
        transaction["date"] = dateutil.parser.parse(transaction["date"]).replace(
            tzinfo=None
        )
        return transaction

    @api.model
    def _wise_transaction_to_lines(self, transaction):
        transaction_type = transaction["type"]
        reference_number = transaction["referenceNumber"]
        details = transaction.get("details", {})
        exchange_details = transaction.get("exchangeDetails")
        recipient = details.get("recipient")
        total_fees = transaction.get("totalFees")
        date = transaction["date"]
        payment_reference = details.get("paymentReference")
        description = details.get("description")
        pay_ref = reference_number
        if description:
            pay_ref = "{}: {}".format(pay_ref, description)
        amount = transaction["amount"]
        amount_value = amount.get("value", 0)
        fees_value = total_fees.get("value", Decimal())
        if transaction_type == "CREDIT" and details.get("type") == "MONEY_ADDED":
            fees_value = fees_value.copy_negate()
        else:
            fees_value = fees_value.copy_sign(amount_value)
        amount_value -= fees_value
        unique_import_id = "{}-{}-{}".format(
            transaction_type,
            reference_number,
            int(date.timestamp()),
        )
        line = {
            "name": payment_reference or description or "",
            "amount": str(amount_value),
            "date": date,
            "payment_ref": pay_ref,
            "unique_import_id": unique_import_id,
        }
        if recipient:
            if "name" in recipient:
                line.update({"partner_name": recipient["name"]})
            if "bankAccount" in recipient:
                line.update({"account_number": recipient["bankAccount"]})
        elif "merchant" in details:
            merchant = details["merchant"]
            if "name" in merchant:
                line.update({"partner_name": merchant["name"]})
        else:
            if "senderName" in details:
                line.update({"partner_name": details["senderName"]})
            if "senderAccount" in details:
                line.update({"account_number": details["senderAccount"]})
        if exchange_details:
            # Handle both old and new exchange details structure
            if "toAmount" in exchange_details and "fromAmount" in exchange_details:
                # New API structure
                to_amount = exchange_details["toAmount"]
                from_amount = exchange_details["fromAmount"]
                other_amount_value = (
                    to_amount["value"]
                    if to_amount["currency"] != amount["currency"]
                    else from_amount["value"]
                )
                other_currency_name = (
                    to_amount["currency"]
                    if to_amount["currency"] != amount["currency"]
                    else from_amount["currency"]
                )
            elif "forAmount" in exchange_details:
                # Old API structure (fallback)
                for_amount = exchange_details["forAmount"]
                other_amount_value = for_amount["value"]
                other_currency_name = for_amount["currency"]
            else:
                # Skip if structure is unknown
                other_amount_value = None
                other_currency_name = None
            
            if other_amount_value and other_currency_name:
                other_amount_value = other_amount_value.copy_abs()
                if amount_value.is_signed():
                    other_amount_value = other_amount_value.copy_negate()
                other_currency = self.env["res.currency"].search(
                    [("name", "=", other_currency_name)], limit=1
                )
                if other_amount_value and other_currency:
                    line.update(
                        {
                            "amount_currency": str(other_amount_value),
                            "currency_id": other_currency.id,
                        }
                    )
        lines = [line]
        if fees_value:
            lines += [
                {
                    "name": _("Fee for %s") % reference_number,
                    "amount": str(fees_value),
                    "date": date,
                    "partner_name": "Wise (former TransferWise)",
                    "unique_import_id": "%s-FEE" % unique_import_id,
                    "payment_ref": _("Transaction fee for %s") % reference_number,
                }
            ]
        return lines

    @api.model
    def _wise_validate(self, content):
        content = json.loads(content, parse_float=Decimal)
        if "error" in content and content["error"]:
            raise UserError(
                content["error_description"]
                if "error_description" in content
                else "Unknown error"
            )
        return content

    @api.model
    def _wise_retrieve(self, url, api_key, private_key=None):
        _logger.debug("Wise API Request: %s", url)
        try:
            with self._wise_urlopen(url, api_key) as response:
                content = response.read().decode(
                    response.headers.get_content_charset() or "utf-8"
                )
                _logger.debug("Wise API Response Status: %s", response.status)
                _logger.debug("Wise API Response Headers: %s", dict(response.headers))
                _logger.debug("Wise API Response Content: %s", content)
        except HTTPError as e:
            _logger.debug("Wise API HTTP Error: %s - %s", e.code, e.reason)
            _logger.debug("Wise API Error Headers: %s", dict(e.headers))
            
            # Handle 403 errors - distinguish between SCA and authentication issues
            if e.code == 403:
                sca_result = e.headers.get("X-2FA-Approval-Result")
                if sca_result == "REJECTED":
                    # This is an SCA-protected endpoint requiring 2FA
                    _logger.debug("Wise API SCA Required - X-2FA-Approval-Result: %s", sca_result)
                    if not private_key:
                        raise UserError(
                            _("Strong Customer Authentication is required but not configured. "
                              "Please configure a private key for SCA.")
                        ) from None
                    
                    one_time_token = e.headers.get("X-2FA-Approval")
                    if not one_time_token:
                        raise UserError(
                            _("SCA required but no One Time Token provided by API")
                        ) from None
                        
                    _logger.debug("Wise API 2FA Required - One Time Token: %s", one_time_token)
                    signature = private_key.sign(
                        one_time_token.encode(),
                        padding.PKCS1v15(),
                        hashes.SHA256(),
                    )
                    signature_b64 = b64encode(signature).decode()
                    _logger.debug("Wise API 2FA Signature: %s", signature_b64)

                    try:
                        with self._wise_urlopen(
                            url,
                            api_key,
                            one_time_token,
                            signature_b64,
                        ) as response:
                            content = response.read().decode(
                                response.headers.get_content_charset() or "utf-8"
                            )
                            _logger.debug("Wise API 2FA Response Status: %s", response.status)
                            _logger.debug("Wise API 2FA Response Headers: %s", dict(response.headers))
                            _logger.debug("Wise API 2FA Response Content: %s", content)
                    except HTTPError as sca_error:
                        _logger.error("Wise API SCA authentication failed after signature")
                        _logger.error("SCA Error Code: %s - %s", sca_error.code, sca_error.reason)
                        _logger.error("SCA Error Headers: %s", dict(sca_error.headers))
                        
                        # Try to get error response body
                        try:
                            sca_error_content = sca_error.read().decode('utf-8')
                            _logger.error("SCA Error Response Body: %s", sca_error_content)
                        except Exception:
                            pass
                        
                        if sca_error.code == 403:
                            sca_result_retry = sca_error.headers.get("X-2FA-Approval-Result")
                            if sca_result_retry == "REJECTED":
                                raise UserError(
                                    _("Strong Customer Authentication failed. The signature was rejected by Wise. "
                                      "Please verify that your private key matches the public key registered with Wise.")
                                ) from None
                            else:
                                raise UserError(
                                    _("Strong Customer Authentication failed with 403 error. "
                                      "This may indicate an issue with the private key or API permissions.")
                                ) from None
                        else:
                            raise UserError(
                                _("Strong Customer Authentication failed with error %s: %s") % (sca_error.code, sca_error.reason)
                            ) from None
                else:
                    # This is a different type of 403 error (authentication, permissions, etc.)
                    _logger.error("Wise API 403 Forbidden without SCA headers. "
                                "This indicates an authentication or permission issue.")
                    _logger.error("Check: 1) API token validity, 2) API token permissions, "
                                "3) Profile access rights, 4) Endpoint availability")
                    
                    # Try to get more details from the response body
                    try:
                        error_content = e.read().decode('utf-8')
                        _logger.error("Wise API Error Response Body: %s", error_content)
                    except Exception:
                        pass
                    
                    raise UserError(
                        _("Wise API authentication failed (403 Forbidden). "
                          "Please check your API token, permissions, and profile access rights. "
                          "See logs for detailed error information.")
                    ) from None
            else:
                # Re-raise non-403 errors
                raise e

        return self._wise_validate(content)

    @api.model
    def _wise_urlopen(self, url, api_key, ott=None, signature=None):
        if not api_key:
            raise UserError(_("No API key specified!"))
        request = urllib.request.Request(url)
        request.add_header("Authorization", "Bearer %s" % api_key)
        if ott and signature:
            request.add_header("X-2FA-Approval", ott)
            request.add_header("X-Signature", signature)
        
        # Log request details with masked API key
        headers_for_log = dict(request.headers)
        if "Authorization" in headers_for_log:
            headers_for_log["Authorization"] = "Bearer " + api_key[:10] + "..." if len(api_key) > 10 else "Bearer ***"
        
        _logger.debug("Wise API Request URL: %s", url)
        _logger.debug("Wise API Request Method: GET")
        _logger.debug("Wise API Request Headers: %s", headers_for_log)
        
        return urllib.request.urlopen(request)

    @api.onchange("certificate_private_key", "service")
    def _onchange_wise_certificate_private_key(self):
        if self.service != "wise":
            return

        self.certificate_public_key = False
        if not self.certificate_private_key:
            return

        try:
            private_key = serialization.load_pem_private_key(
                self.certificate_private_key.encode(),
                password=None,
                backend=default_backend(),
            )
            self.certificate_public_key = (
                private_key.public_key()
                .public_bytes(
                    serialization.Encoding.PEM,
                    serialization.PublicFormat.PKCS1,
                )
                .decode()
            )
        except BaseException:
            _logger.warning("Unable to parse key", exc_info=True)
            raise UserError(_("Unable to parse key")) from None

    def _wise_generate_key(self):
        self.ensure_one()

        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend(),
        )
        self.certificate_private_key = private_key.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.TraditionalOpenSSL,  # a.k.a. PKCS#1
            serialization.NoEncryption(),
        ).decode()

        self.certificate_public_key = (
            private_key.public_key()
            .public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.PKCS1,
            )
            .decode()
        )

    def button_wise_generate_key(self):
        for provider in self:
            provider._wise_generate_key()
