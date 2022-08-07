# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2021 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import itertools
import json
import urllib.request
from base64 import b64encode
from datetime import datetime
from decimal import Decimal
from urllib.error import HTTPError
from urllib.parse import urlencode

import dateutil.parser
import pytz
from dateutil.relativedelta import relativedelta

from odoo import _, api, models
from odoo.exceptions import UserError

PAYPAL_API_BASE = "https://api.paypal.com"
TRANSACTIONS_SCOPE = "https://uri.paypal.com/services/reporting/search/read"
EVENT_DESCRIPTIONS = {
    "T0000": _("General PayPal-to-PayPal payment"),
    "T0001": _("MassPay payment"),
    "T0002": _("Subscription payment"),
    "T0003": _("Pre-approved payment (BillUser API)"),
    "T0004": _("eBay auction payment"),
    "T0005": _("Direct payment API"),
    "T0006": _("PayPal Checkout APIs"),
    "T0007": _("Website payments standard payment"),
    "T0008": _("Postage payment to carrier"),
    "T0009": _("Gift certificate payment, purchase of gift certificate"),
    "T0010": _("Third-party auction payment"),
    "T0011": _("Mobile payment, made through a mobile phone"),
    "T0012": _("Virtual terminal payment"),
    "T0013": _("Donation payment"),
    "T0014": _("Rebate payments"),
    "T0015": _("Third-party payout"),
    "T0016": _("Third-party recoupment"),
    "T0017": _("Store-to-store transfers"),
    "T0018": _("PayPal Here payment"),
    "T0019": _("Generic instrument-funded payment"),
    "T0100": _("General non-payment fee"),
    "T0101": _("Website payments. Pro account monthly fee"),
    "T0102": _("Foreign bank withdrawal fee"),
    "T0103": _("WorldLink check withdrawal fee"),
    "T0104": _("Mass payment batch fee"),
    "T0105": _("Check withdrawal"),
    "T0106": _("Chargeback processing fee"),
    "T0107": _("Payment fee"),
    "T0108": _("ATM withdrawal"),
    "T0109": _("Auto-sweep from account"),
    "T0110": _("International credit card withdrawal"),
    "T0111": _("Warranty fee for warranty purchase"),
    "T0112": _("Gift certificate expiration fee"),
    "T0113": _("Partner fee"),
    "T0200": _("General currency conversion"),
    "T0201": _("User-initiated currency conversion"),
    "T0202": _("Currency conversion required to cover negative balance"),
    "T0300": _("General funding of PayPal account"),
    "T0301": _("PayPal balance manager funding of PayPal account"),
    "T0302": _("ACH funding for funds recovery from account balance"),
    "T0303": _("Electronic funds transfer (EFT)"),
    "T0400": _("General withdrawal from PayPal account"),
    "T0401": _("AutoSweep"),
    "T0500": _("General PayPal debit card transaction"),
    "T0501": _("Virtual PayPal debit card transaction"),
    "T0502": _("PayPal debit card withdrawal to ATM"),
    "T0503": _("Hidden virtual PayPal debit card transaction"),
    "T0504": _("PayPal debit card cash advance"),
    "T0505": _("PayPal debit authorization"),
    "T0600": _("General credit card withdrawal"),
    "T0700": _("General credit card deposit"),
    "T0701": _("Credit card deposit for negative PayPal account balance"),
    "T0800": _("General bonus"),
    "T0801": _("Debit card cash back bonus"),
    "T0802": _("Merchant referral account bonus"),
    "T0803": _("Balance manager account bonus"),
    "T0804": _("PayPal buyer warranty bonus"),
    "T0805": _(
        "PayPal protection bonus, payout for PayPal buyer protection, payout "
        "for full protection with PayPal buyer credit."
    ),
    "T0806": _("Bonus for first ACH use"),
    "T0807": _("Credit card security charge refund"),
    "T0808": _("Credit card cash back bonus"),
    "T0900": _("General incentive or certificate redemption"),
    "T0901": _("Gift certificate redemption"),
    "T0902": _("Points incentive redemption"),
    "T0903": _("Coupon redemption"),
    "T0904": _("eBay loyalty incentive"),
    "T0905": _("Offers used as funding source"),
    "T1000": _("Bill pay transaction"),
    "T1100": _("General reversal"),
    "T1101": _("Reversal of ACH withdrawal transaction"),
    "T1102": _("Reversal of debit card transaction"),
    "T1103": _("Reversal of points usage"),
    "T1104": _("Reversal of ACH deposit"),
    "T1105": _("Reversal of general account hold"),
    "T1106": _("Payment reversal, initiated by PayPal"),
    "T1107": _("Payment refund, initiated by merchant"),
    "T1108": _("Fee reversal"),
    "T1109": _("Fee refund"),
    "T1110": _("Hold for dispute investigation"),
    "T1111": _("Cancellation of hold for dispute resolution"),
    "T1112": _("MAM reversal"),
    "T1113": _("Non-reference credit payment"),
    "T1114": _("MassPay reversal transaction"),
    "T1115": _("MassPay refund transaction"),
    "T1116": _("Instant payment review (IPR) reversal"),
    "T1117": _("Rebate or cash back reversal"),
    "T1118": _("Generic instrument/Open Wallet reversals (seller side)"),
    "T1119": _("Generic instrument/Open Wallet reversals (buyer side)"),
    "T1200": _("General account adjustment"),
    "T1201": _("Chargeback"),
    "T1202": _("Chargeback reversal"),
    "T1203": _("Charge-off adjustment"),
    "T1204": _("Incentive adjustment"),
    "T1205": _("Reimbursement of chargeback"),
    "T1207": _("Chargeback re-presentment rejection"),
    "T1208": _("Chargeback cancellation"),
    "T1300": _("General authorization"),
    "T1301": _("Reauthorization"),
    "T1302": _("Void of authorization"),
    "T1400": _("General dividend"),
    "T1500": _("General temporary hold"),
    "T1501": _("Account hold for open authorization"),
    "T1502": _("Account hold for ACH deposit"),
    "T1503": _("Temporary hold on available balance"),
    "T1600": _("PayPal buyer credit payment funding"),
    "T1601": _("BML credit, transfer from BML"),
    "T1602": _("Buyer credit payment"),
    "T1603": _("Buyer credit payment withdrawal, transfer to BML"),
    "T1700": _("General withdrawal to non-bank institution"),
    "T1701": _("WorldLink withdrawal"),
    "T1800": _("General buyer credit payment"),
    "T1801": _("BML withdrawal, transfer to BML"),
    "T1900": _("General adjustment without business-related event"),
    "T2000": _("General intra-account transfer"),
    "T2001": _("Settlement consolidation"),
    "T2002": _("Transfer of funds from payable"),
    "T2003": _("Transfer to external GL entity"),
    "T2101": _("General hold"),
    "T2102": _("General hold release"),
    "T2103": _("Reserve hold"),
    "T2104": _("Reserve release"),
    "T2105": _("Payment review hold"),
    "T2106": _("Payment review release"),
    "T2107": _("Payment hold"),
    "T2108": _("Payment hold release"),
    "T2109": _("Gift certificate purchase"),
    "T2110": _("Gift certificate redemption"),
    "T2111": _("Funds not yet available"),
    "T2112": _("Funds available"),
    "T2113": _("Blocked payments"),
    "T2201": _("Transfer to and from a credit-card-funded restricted balance"),
    "T3000": _("Generic instrument/Open Wallet transaction"),
    "T5000": _("Deferred disbursement, funds collected for disbursement"),
    "T5001": _("Delayed disbursement, funds disbursed"),
    "T9700": _("Account receivable for shipping"),
    "T9701": _("Funds payable: PayPal-provided funds that must be paid back"),
    "T9702": _("Funds receivable: PayPal-provided funds that are being paid back"),
    "T9800": _("Display only transaction"),
    "T9900": _("Other"),
}
NO_DATA_FOR_DATE_AVAIL_MSG = "Data for the given start date is not available."


class OnlineBankStatementProviderPayPal(models.Model):
    _inherit = "online.bank.statement.provider"

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("paypal", "PayPal.com"),
        ]

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "paypal":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        currency = (self.currency_id or self.company_id.currency_id).name

        if date_since.tzinfo:
            date_since = date_since.astimezone(pytz.utc).replace(tzinfo=None)
        if date_until.tzinfo:
            date_until = date_until.astimezone(pytz.utc).replace(tzinfo=None)

        if date_since < datetime.utcnow() - relativedelta(years=3):
            raise UserError(
                _(
                    "PayPal allows retrieving transactions only up to 3 years in "
                    "the past. Please import older transactions manually. See "
                    "https://www.paypal.com/us/smarthelp/article/why-can't-i"
                    "-access-transaction-history-greater-than-3-years-ts2241"
                )
            )

        token = self._paypal_get_token()
        transactions = self._paypal_get_transactions(
            token, currency, date_since, date_until
        )
        if not transactions:
            balance = self._paypal_get_balance(token, currency, date_since)
            return [], {"balance_start": balance, "balance_end_real": balance}

        # Normalize transactions, sort by date, and get lines
        transactions = list(
            sorted(
                transactions,
                key=lambda transaction: self._paypal_get_transaction_date(transaction),
            )
        )
        lines = list(
            itertools.chain.from_iterable(
                map(lambda x: self._paypal_transaction_to_lines(x), transactions)
            )
        )

        first_transaction = transactions[0]
        first_transaction_id = first_transaction["transaction_info"]["transaction_id"]
        first_transaction_date = self._paypal_get_transaction_date(first_transaction)
        first_transaction = self._paypal_get_transaction(
            token, first_transaction_id, first_transaction_date
        )
        if not first_transaction:
            raise UserError(
                _("Failed to resolve transaction %s (%s)")
                % (first_transaction_id, first_transaction_date)
            )
        balance_start = self._paypal_get_transaction_ending_balance(first_transaction)
        balance_start -= self._paypal_get_transaction_total_amount(first_transaction)
        balance_start -= self._paypal_get_transaction_fee_amount(first_transaction)

        last_transaction = transactions[-1]
        last_transaction_id = last_transaction["transaction_info"]["transaction_id"]
        last_transaction_date = self._paypal_get_transaction_date(last_transaction)
        last_transaction = self._paypal_get_transaction(
            token, last_transaction_id, last_transaction_date
        )
        if not last_transaction:
            raise UserError(
                _("Failed to resolve transaction %s (%s)")
                % (last_transaction_id, last_transaction_date)
            )
        balance_end = self._paypal_get_transaction_ending_balance(last_transaction)

        return lines, {"balance_start": balance_start, "balance_end_real": balance_end}

    @api.model
    def _paypal_preparse_transaction(self, transaction):
        date = (
            dateutil.parser.parse(self._paypal_get_transaction_date(transaction))
            .astimezone(pytz.utc)
            .replace(tzinfo=None)
        )
        transaction["transaction_info"]["transaction_updated_date"] = date
        return transaction

    @api.model
    def _paypal_transaction_to_lines(self, data):
        transaction = data["transaction_info"]
        payer = data["payer_info"]
        transaction_id = transaction["transaction_id"]
        event_code = transaction["transaction_event_code"]
        date = self._paypal_get_transaction_date(data)
        total_amount = self._paypal_get_transaction_total_amount(data)
        fee_amount = self._paypal_get_transaction_fee_amount(data)
        transaction_subject = transaction.get("transaction_subject")
        transaction_note = transaction.get("transaction_note")
        invoice = transaction.get("invoice_id")
        payer_name = payer.get("payer_name", {})
        payer_email = payer_name.get("email_address")
        if invoice:
            invoice = _("Invoice %s") % invoice
        note = transaction_id
        if transaction_subject or transaction_note:
            note = "{}: {}".format(note, transaction_subject or transaction_note)
        if payer_email:
            note += " (%s)" % payer_email
        unique_import_id = "{}-{}".format(transaction_id, int(date.timestamp()))
        name = (
            invoice
            or transaction_subject
            or transaction_note
            or EVENT_DESCRIPTIONS.get(event_code)
            or ""
        )
        line = {
            "ref": name,
            "amount": str(total_amount),
            "date": date,
            "payment_ref": note,
            "unique_import_id": unique_import_id,
            "raw_data": transaction,
        }
        payer_full_name = payer_name.get("full_name") or payer_name.get(
            "alternate_full_name"
        )
        if payer_full_name:
            line.update({"partner_name": payer_full_name})
        lines = [line]
        if fee_amount:
            lines += [
                {
                    "ref": _("Fee for %s") % (name or transaction_id),
                    "amount": str(fee_amount),
                    "date": date,
                    "partner_name": "PayPal",
                    "unique_import_id": "%s-FEE" % unique_import_id,
                    "payment_ref": _("Transaction fee for %s") % note,
                }
            ]
        return lines

    def _paypal_get_token(self):
        self.ensure_one()
        data = self._paypal_retrieve(
            (self.api_base or PAYPAL_API_BASE) + "/v1/oauth2/token",
            (self.username, self.password),
            data=urlencode({"grant_type": "client_credentials"}).encode("utf-8"),
        )
        if "scope" not in data or TRANSACTIONS_SCOPE not in data["scope"]:
            raise UserError(_("PayPal App features are configured incorrectly!"))
        if "token_type" not in data or data["token_type"] != "Bearer":
            raise UserError(_("Invalid token type!"))
        if "access_token" not in data:
            raise UserError(_("Failed to acquire token using Client ID and Secret!"))
        return data["access_token"]

    def _paypal_get_balance(self, token, currency, as_of_timestamp):
        self.ensure_one()
        url = (
            self.api_base or PAYPAL_API_BASE
        ) + "/v1/reporting/balances?currency_code={}&as_of_time={}".format(
            currency,
            as_of_timestamp.isoformat() + "Z",
        )
        data = self._paypal_retrieve(url, token)
        available_balance = data["balances"][0].get("available_balance")
        if not available_balance:
            return Decimal()
        return Decimal(available_balance["value"])

    def _paypal_get_transaction(self, token, transaction_id, timestamp):
        self.ensure_one()
        transaction_date = timestamp.isoformat() + "Z"
        url = (
            (self.api_base or PAYPAL_API_BASE)
            + "/v1/reporting/transactions"
            + ("?start_date=%s" "&end_date=%s" "&fields=all")
            % (
                transaction_date,
                transaction_date,
            )
        )
        data = self._paypal_retrieve(url, token)
        transactions = data["transaction_details"]
        for transaction in transactions:
            if transaction["transaction_info"]["transaction_id"] != transaction_id:
                continue
            return transaction
        return None

    def _paypal_get_transactions(self, token, currency, since, until):
        self.ensure_one()
        # NOTE: Not more than 31 days in a row
        # NOTE: start_date <= date <= end_date, thus check every transaction
        interval_step = relativedelta(days=31)
        interval_start = since
        transactions = []
        while interval_start < until:
            interval_end = min(interval_start + interval_step, until)
            page = 1
            total_pages = None
            while total_pages is None or page <= total_pages:
                url = (
                    (self.api_base or PAYPAL_API_BASE)
                    + "/v1/reporting/transactions"
                    + (
                        "?transaction_currency=%s"
                        "&start_date=%s"
                        "&end_date=%s"
                        "&fields=all"
                        "&balance_affecting_records_only=Y"
                        "&page_size=500"
                        "&page=%d"
                        % (
                            currency,
                            interval_start.isoformat() + "Z",
                            interval_end.isoformat() + "Z",
                            page,
                        )
                    )
                )

                # NOTE: Workaround for INVALID_REQUEST (see ROADMAP.rst)
                invalid_data_workaround = self.env.context.get(
                    "test_account_statement_import_online_paypal_monday",
                    interval_start.weekday() == 0
                    and (datetime.utcnow() - interval_start).total_seconds() < 28800,
                )

                data = self.with_context(
                    invalid_data_workaround=invalid_data_workaround,
                )._paypal_retrieve(url, token)
                interval_transactions = map(
                    lambda transaction: self._paypal_preparse_transaction(transaction),
                    data["transaction_details"],
                )
                transactions += list(
                    filter(
                        lambda transaction: interval_start
                        <= self._paypal_get_transaction_date(transaction)
                        < interval_end,
                        interval_transactions,
                    )
                )
                total_pages = data["total_pages"]
                page += 1
            interval_start += interval_step
        return transactions

    @api.model
    def _paypal_get_transaction_date(self, transaction):
        # NOTE: CSV reports from PayPal use this date, search as well
        return transaction["transaction_info"]["transaction_updated_date"]

    @api.model
    def _paypal_get_transaction_total_amount(self, transaction):
        transaction_amount = transaction["transaction_info"].get("transaction_amount")
        if not transaction_amount:
            return Decimal()
        return Decimal(transaction_amount["value"])

    @api.model
    def _paypal_get_transaction_fee_amount(self, transaction):
        fee_amount = transaction["transaction_info"].get("fee_amount")
        if not fee_amount:
            return Decimal()
        return Decimal(fee_amount["value"])

    @api.model
    def _paypal_get_transaction_ending_balance(self, transaction):
        # NOTE: 'available_balance' instead of 'ending_balance' as per CSV file
        transaction_amount = transaction["transaction_info"].get("available_balance")
        if not transaction_amount:
            return Decimal()
        return Decimal(transaction_amount["value"])

    @api.model
    def _paypal_decode_error(self, content):
        if "name" in content:
            return UserError(
                "%s: %s"
                % (
                    content["name"],
                    content.get("message", _("Unknown error")),
                )
            )

        if "error" in content:
            return UserError(
                "%s: %s"
                % (
                    content["error"],
                    content.get("error_description", _("Unknown error")),
                )
            )

        return None

    @api.model
    def _paypal_retrieve(self, url, auth, data=None):
        try:
            with self._paypal_urlopen(url, auth, data) as response:
                content = response.read().decode("utf-8")
        except HTTPError as e:
            content = json.loads(e.read().decode("utf-8"))

            # NOTE: Workaround for INVALID_REQUEST (see ROADMAP.rst)
            if (
                self.env.context.get("invalid_data_workaround")
                and content.get("name") == "INVALID_REQUEST"
                and content.get("message") == NO_DATA_FOR_DATE_AVAIL_MSG
            ):
                return {
                    "transaction_details": [],
                    "page": 1,
                    "total_items": 0,
                    "total_pages": 0,
                }

            raise self._paypal_decode_error(content) or e
        return json.loads(content)

    @api.model
    def _paypal_urlopen(self, url, auth, data=None):
        if not auth:
            raise UserError(_("No authentication specified!"))
        request = urllib.request.Request(url, data=data)
        if isinstance(auth, tuple):
            request.add_header(
                "Authorization",
                "Basic %s"
                % str(
                    b64encode(("{}:{}".format(auth[0], auth[1])).encode("utf-8")),
                    "utf-8",
                ),
            )
        elif isinstance(auth, str):
            request.add_header("Authorization", "Bearer %s" % auth)
        else:
            raise UserError(_("Unknown authentication specified!"))
        return urllib.request.urlopen(request)
