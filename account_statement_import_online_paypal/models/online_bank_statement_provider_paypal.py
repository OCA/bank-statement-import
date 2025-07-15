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

from odoo import api, models
from odoo.exceptions import UserError
from odoo.tools import LazyTranslate

_lt = LazyTranslate(__name__, default_lang="en_US")

PAYPAL_API_BASE = "https://api.paypal.com"
TRANSACTIONS_SCOPE = "https://uri.paypal.com/services/reporting/search/read"
EVENT_DESCRIPTIONS = {
    "T0000": _lt("General PayPal-to-PayPal payment"),
    "T0001": _lt("MassPay payment"),
    "T0002": _lt("Subscription payment"),
    "T0003": _lt("Pre-approved payment (BillUser API)"),
    "T0004": _lt("eBay auction payment"),
    "T0005": _lt("Direct payment API"),
    "T0006": _lt("PayPal Checkout APIs"),
    "T0007": _lt("Website payments standard payment"),
    "T0008": _lt("Postage payment to carrier"),
    "T0009": _lt("Gift certificate payment, purchase of gift certificate"),
    "T0010": _lt("Third-party auction payment"),
    "T0011": _lt("Mobile payment, made through a mobile phone"),
    "T0012": _lt("Virtual terminal payment"),
    "T0013": _lt("Donation payment"),
    "T0014": _lt("Rebate payments"),
    "T0015": _lt("Third-party payout"),
    "T0016": _lt("Third-party recoupment"),
    "T0017": _lt("Store-to-store transfers"),
    "T0018": _lt("PayPal Here payment"),
    "T0019": _lt("Generic instrument-funded payment"),
    "T0100": _lt("General non-payment fee"),
    "T0101": _lt("Website payments. Pro account monthly fee"),
    "T0102": _lt("Foreign bank withdrawal fee"),
    "T0103": _lt("WorldLink check withdrawal fee"),
    "T0104": _lt("Mass payment batch fee"),
    "T0105": _lt("Check withdrawal"),
    "T0106": _lt("Chargeback processing fee"),
    "T0107": _lt("Payment fee"),
    "T0108": _lt("ATM withdrawal"),
    "T0109": _lt("Auto-sweep from account"),
    "T0110": _lt("International credit card withdrawal"),
    "T0111": _lt("Warranty fee for warranty purchase"),
    "T0112": _lt("Gift certificate expiration fee"),
    "T0113": _lt("Partner fee"),
    "T0200": _lt("General currency conversion"),
    "T0201": _lt("User-initiated currency conversion"),
    "T0202": _lt("Currency conversion required to cover negative balance"),
    "T0300": _lt("General funding of PayPal account"),
    "T0301": _lt("PayPal balance manager funding of PayPal account"),
    "T0302": _lt("ACH funding for funds recovery from account balance"),
    "T0303": _lt("Electronic funds transfer (EFT)"),
    "T0400": _lt("General withdrawal from PayPal account"),
    "T0401": _lt("AutoSweep"),
    "T0402": _lt("Withdrawal to Hyperwallet"),
    "T0403": _lt(
        "Withdrawals initiated by user manually. Not related to automated "
        "scheduled withdrawals"
    ),
    "T0500": _lt("General PayPal debit card transaction"),
    "T0501": _lt("Virtual PayPal debit card transaction"),
    "T0502": _lt("PayPal debit card withdrawal to ATM"),
    "T0503": _lt("Hidden virtual PayPal debit card transaction"),
    "T0504": _lt("PayPal debit card cash advance"),
    "T0505": _lt("PayPal debit authorization"),
    "T0600": _lt("General credit card withdrawal"),
    "T0700": _lt("General credit card deposit"),
    "T0701": _lt("Credit card deposit for negative PayPal account balance"),
    "T0800": _lt("General bonus"),
    "T0801": _lt("Debit card cash back bonus"),
    "T0802": _lt("Merchant referral account bonus"),
    "T0803": _lt("Balance manager account bonus"),
    "T0804": _lt("PayPal buyer warranty bonus"),
    "T0805": _lt(
        "PayPal protection bonus, payout for PayPal buyer protection, payout "
        "for full protection with PayPal buyer credit."
    ),
    "T0806": _lt("Bonus for first ACH use"),
    "T0807": _lt("Credit card security charge refund"),
    "T0808": _lt("Credit card cash back bonus"),
    "T0900": _lt("General incentive or certificate redemption"),
    "T0901": _lt("Gift certificate redemption"),
    "T0902": _lt("Points incentive redemption"),
    "T0903": _lt("Coupon redemption"),
    "T0904": _lt("eBay loyalty incentive"),
    "T0905": _lt("Offers used as funding source"),
    "T1000": _lt("Bill pay transaction"),
    "T1100": _lt("General reversal"),
    "T1101": _lt("Reversal of ACH withdrawal transaction"),
    "T1102": _lt("Reversal of debit card transaction"),
    "T1103": _lt("Reversal of points usage"),
    "T1104": _lt("Reversal of ACH deposit"),
    "T1105": _lt("Reversal of general account hold"),
    "T1106": _lt("Payment reversal, initiated by PayPal"),
    "T1107": _lt("Payment refund, initiated by merchant"),
    "T1108": _lt("Fee reversal"),
    "T1109": _lt("Fee refund"),
    "T1110": _lt("Hold for dispute investigation"),
    "T1111": _lt("Cancellation of hold for dispute resolution"),
    "T1112": _lt("MAM reversal"),
    "T1113": _lt("Non-reference credit payment"),
    "T1114": _lt("MassPay reversal transaction"),
    "T1115": _lt("MassPay refund transaction"),
    "T1116": _lt("Instant payment review (IPR) reversal"),
    "T1117": _lt("Rebate or cash back reversal"),
    "T1118": _lt("Generic instrument/Open Wallet reversals (seller side)"),
    "T1119": _lt("Generic instrument/Open Wallet reversals (buyer side)"),
    "T1200": _lt("General account adjustment"),
    "T1201": _lt("Chargeback"),
    "T1202": _lt("Chargeback reversal"),
    "T1203": _lt("Charge-off adjustment"),
    "T1204": _lt("Incentive adjustment"),
    "T1205": _lt("Reimbursement of chargeback"),
    "T1207": _lt("Chargeback re-presentment rejection"),
    "T1208": _lt("Chargeback cancellation"),
    "T1300": _lt("General authorization"),
    "T1301": _lt("Reauthorization"),
    "T1302": _lt("Void of authorization"),
    "T1400": _lt("General dividend"),
    "T1500": _lt("General temporary hold"),
    "T1501": _lt("Account hold for open authorization"),
    "T1502": _lt("Account hold for ACH deposit"),
    "T1503": _lt("Temporary hold on available balance"),
    "T1600": _lt("PayPal buyer credit payment funding"),
    "T1601": _lt("BML credit, transfer from BML"),
    "T1602": _lt("Buyer credit payment"),
    "T1603": _lt("Buyer credit payment withdrawal, transfer to BML"),
    "T1700": _lt("General withdrawal to non-bank institution"),
    "T1701": _lt("WorldLink withdrawal"),
    "T1800": _lt("General buyer credit payment"),
    "T1801": _lt("BML withdrawal, transfer to BML"),
    "T1900": _lt("General adjustment without business-related event"),
    "T2000": _lt("General intra-account transfer"),
    "T2001": _lt("Settlement consolidation"),
    "T2002": _lt("Transfer of funds from payable"),
    "T2003": _lt("Transfer to external GL entity"),
    "T2004": _lt("Receivables financing - Applicable only in Brazil"),
    "T2101": _lt("General hold"),
    "T2102": _lt("General hold release"),
    "T2103": _lt("Reserve hold"),
    "T2104": _lt("Reserve release"),
    "T2105": _lt("Payment review hold"),
    "T2106": _lt("Payment review release"),
    "T2107": _lt("Payment hold"),
    "T2108": _lt("Payment hold release"),
    "T2109": _lt("Gift certificate purchase"),
    "T2110": _lt("Gift certificate redemption"),
    "T2111": _lt("Funds not yet available"),
    "T2112": _lt("Funds available"),
    "T2113": _lt("Blocked payments"),
    "T2114": _lt("Tax hold"),
    "T2201": _lt("Transfer to and from a credit-card-funded restricted balance"),
    "T2301": _lt("Tax withholding to IRS"),
    "T3000": _lt("Generic instrument/Open Wallet transaction"),
    "T5000": _lt("Deferred disbursement, funds collected for disbursement"),
    "T5001": _lt("Delayed disbursement, funds disbursed"),
    "T9700": _lt("Account receivable for shipping"),
    "T9701": _lt("Funds payable: PayPal-provided funds that must be paid back"),
    "T9702": _lt("Funds receivable: PayPal-provided funds that are being paid back"),
    "T9800": _lt("Display only transaction"),
    "T9900": _lt("Other"),
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
                self.env._(
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
                self.env._(
                    "Failed to resolve transaction %(first_transaction_id)s "
                    "(%(first_transaction_date)s)",
                    first_transaction_id=first_transaction_id,
                    first_transaction_date=first_transaction_date,
                )
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
                self.env._(
                    "Failed to resolve transaction %(last_transaction_id)s "
                    "(%(last_transaction_date)s)",
                    last_transaction_id=last_transaction_id,
                    last_transaction_date=last_transaction_date,
                )
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
            invoice = self.env._("Invoice %s") % invoice
        note = transaction_id
        if transaction_subject or transaction_note:
            note = f"{note}: {transaction_subject or transaction_note}"
        if payer_email:
            note += f" ({payer_email})"
        unique_import_id = f"{transaction_id}-{int(date.timestamp())}"
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
                    "ref": self.env._("Fee for %s") % (name or transaction_id),
                    "amount": str(fee_amount),
                    "date": date,
                    "partner_name": "PayPal",
                    "unique_import_id": f"{unique_import_id}-FEE",
                    "payment_ref": self.env._("Transaction fee for %s") % note,
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
            raise UserError(
                self.env._("PayPal App features are configured incorrectly!")
            )
        if "token_type" not in data or data["token_type"] != "Bearer":
            raise UserError(self.env._("Invalid token type!"))
        if "access_token" not in data:
            raise UserError(
                self.env._("Failed to acquire token using Client ID and Secret!")
            )
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
        transaction_date_ini = (timestamp - relativedelta(seconds=1)).isoformat() + "Z"
        transaction_date_end = (timestamp + relativedelta(seconds=1)).isoformat() + "Z"
        url = (
            (self.api_base or PAYPAL_API_BASE)
            + "/v1/reporting/transactions"
            + (
                f"?start_date={transaction_date_ini}"
                f"&end_date={transaction_date_end}"
                "&fields=all"
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
                "{}: {}".format(
                    content["name"],
                    content.get("message", self.env._("Unknown error")),
                )
            )

        if "error" in content:
            return UserError(
                "{}: {}".format(
                    content["error"],
                    content.get("error_description", self.env._("Unknown error")),
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

            raise self._paypal_decode_error(content) or e from None
        return json.loads(content)

    @api.model
    def _paypal_urlopen(self, url, auth, data=None):
        if not auth:
            raise UserError(self.env._("No authentication specified!"))
        request = urllib.request.Request(url, data=data)
        if isinstance(auth, tuple):
            request.add_header(
                "Authorization",
                "Basic {}".format(
                    str(
                        b64encode((f"{auth[0]}:{auth[1]}").encode()),
                        "utf-8",
                    ),
                ),
            )
        elif isinstance(auth, str):
            request.add_header("Authorization", f"Bearer {auth}")
        else:
            raise UserError(self.env._("Unknown authentication specified!"))
        return urllib.request.urlopen(request)
