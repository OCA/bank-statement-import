# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from base64 import b64encode
from csv import reader as CsvReader
from datetime import datetime
import dateutil.parser
from decimal import Decimal
from io import StringIO
import itertools
import json
import logging
import pytz
import urllib.request

from odoo import api, fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    import braintree
except (ImportError, IOError) as err:  # pragma: no cover
    _logger.error(err)

BRAINTREE_GQL_ENDPOINT = "https://payments.braintree-api.com/graphql"


class OnlineBankStatementProviderBraintree(models.Model):
    _inherit = "online.bank.statement.provider"

    # NOTE: This is needed to workaround possible multiple 'origin' fields
    # present in the same view, resulting in wrong field view configuraion
    # if more than one is widget="dynamic_dropdown"
    braintree_merchant_account = fields.Char(
        related='origin',
        readonly=False,
    )

    @api.model
    def values_braintree_merchant_accounts(self):
        api_base = self.env.context.get("api_base") or BRAINTREE_GQL_ENDPOINT
        username = self.env.context.get("username")
        password = self.env.context.get("password")
        if not username or not password:
            return []
        credentials = self._get_braintree_credentials(username, password)

        try:
            response = self._braintree_query(credentials, api_base, """
                query {
                    viewer {
                        merchant {
                            id
                        }
                    }
                }
            """)
            response = self._validate_braintree_response(response)
            merchant_id = response["data"]["viewer"]["merchant"]["id"]

            # NOTE: This API is not exposed via GraphQL for some reason
            gateway = braintree.BraintreeGateway(
                braintree.Configuration(
                    environment=braintree.Environment.Production,
                    merchant_id=merchant_id,
                    public_key=username,
                    private_key=password,
                )
            )
            return list(map(
                lambda merchant_account: (
                    str(merchant_account.id),
                    str(merchant_account.id),
                ),
                gateway.merchant_account.all().merchant_accounts
            ))
        except:
            _logger.warning("Failed to query merchant accounts", exc_info=True)
            return []

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("braintree", "BraintreePayments.com"),
        ]

    @api.multi
    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "braintree":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        if not self.username:
            raise UserError(_("Public Key not specified!"))
        if not self.password:
            raise UserError(_("Private Key not specified!"))
        if not self.origin:
            raise UserError(_("Merchant Account not specified!"))

        api_base = self.api_base or BRAINTREE_GQL_ENDPOINT
        credentials = self._get_braintree_credentials(
            self.username,
            self.password,
        )
        currency = (
            self.currency_id or self.company_id.currency_id
        ).name

        if date_since.tzinfo:
            date_since = date_since.astimezone(pytz.utc).replace(tzinfo=None)
        if date_until.tzinfo:
            date_until = date_until.astimezone(pytz.utc).replace(tzinfo=None)

        transactions = []
        transactions_by_id = {}
        query_cursor = None
        while True:
            _logger.debug("_braintree_query: transactions")
            response = self._braintree_query(credentials, api_base, """
                query {
                    search {
                        transactions(
                            after: %(CURSOR)s,
                            input: {
                                statusTransition: {
                                    settledAt: {
                                        greaterThanOrEqualTo: "%(SINCE)sZ",
                                        lessThanOrEqualTo: "%(UNTIL)sZ"
                                    }
                                }
                            }
                        ) {
                            edges {
                                node {
                                    id
                                    ... on Transaction {
                                        legacyId
                                        merchantAccountId
                                        amount {
                                            value
                                            currencyIsoCode
                                        }
                                        statusHistory {
                                            status
                                            terminal
                                            timestamp
                                        }
                                        disbursementDetails {
                                            date
                                            amount {
                                                value
                                                currencyIsoCode
                                            }
                                            exchangeRate
                                            fundsHeld
                                        }
                                    }
                                }
                            }
                            pageInfo {
                                hasNextPage
                                endCursor
                            }
                        }
                    }
                }
            """ % {
                "CURSOR": (
                    "null"
                    if query_cursor is None
                    else "\"%s\"" % query_cursor
                ),
                "SINCE": date_since.isoformat(),
                "UNTIL": date_until.isoformat(),
            })
            response = self._validate_braintree_response(response)
            search_result = response["data"]["search"]["transactions"]

            for entry in search_result["edges"]:
                if entry["node"]["merchantAccountId"] != self.origin:
                    continue

                terminal_statuses = [
                    status
                    for status in entry["node"]["statusHistory"]
                    if status["terminal"] and status["status"] == "SETTLED"
                ]
                if len(terminal_statuses) == 0:
                    continue
                status = terminal_statuses[0]

                transaction = {
                    "id": entry["node"]["id"],
                    "merchant_account": entry["node"]["merchantAccountId"],
                    "settlement_date": dateutil.parser.parse(
                        status["timestamp"]
                    ).date(),
                    "presentment_currency": (
                        entry["node"]["amount"]["currencyIsoCode"]
                    ),
                    "presentment_amount": self._parse_decimal(
                        entry["node"]["amount"]["value"]
                    ),
                }

                disbursement_details = entry["node"]["disbursementDetails"]
                if disbursement_details is None:
                    # NOTE: Without disbursement date, settlement amount can't
                    # be resolved as well as fees.
                    continue

                transactions_by_id[transaction["id"]] = transaction
                transactions.append(transaction)

                if entry["node"].get("legacyId"):
                    legacy_id = entry["node"]["legacyId"]
                    transaction.update({
                        "legacy_id": legacy_id,
                    })
                    transactions_by_id[legacy_id] = transaction

                disbursement_details = entry["node"]["disbursementDetails"]

                disbursement_currency = \
                    disbursement_details["amount"]["currencyIsoCode"]
                if disbursement_currency != currency:
                    raise UserError(_(
                        "Disbursement currency %(DISBURCEMENT)s differs "
                        "from journal currency %(JOURNAL)s"
                    ) % {
                        "DISBURCEMENT": disbursement_currency,
                        "JOURNAL": disbursement_currency,
                    })
                transaction.update({
                    "disbursement_date": datetime.strptime(
                        disbursement_details["date"],
                        "%Y-%m-%d"
                    ).date(),
                    "disbursement_currency": disbursement_currency,
                    "disbursement_amount": Decimal(),
                })
                if not disbursement_details["fundsHeld"]:
                    transaction.update({
                        "disbursement_amount": self._parse_decimal(
                            disbursement_details["amount"]["value"]
                        ),
                    })

            if search_result["pageInfo"]["hasNextPage"]:
                query_cursor = search_result["pageInfo"]["endCursor"]
                continue
            break

        disbursement_dates = list(set(map(
            lambda transaction: transaction["disbursement_date"],
            filter(
                lambda transaction: "disbursement_date" in transaction,
                transactions
            )
        )))
        for disbursement_date in disbursement_dates:
            _logger.info("_braintree_query: paymentLevelFees(%s)" % (
                disbursement_date,
            ))
            response = self._braintree_query(credentials, api_base, """
                query {
                    report {
                        paymentLevelFees(
                            date: "%(DATE)s",
                            merchantAccountId: "%(MERCHANT_ACCOUNT_ID)s"
                        ) {
                            url
                        }
                    }
                }
            """ % {
                "DATE": disbursement_date,
                "MERCHANT_ACCOUNT_ID": self.origin,
            })
            response = self._validate_braintree_response(response)
            payment_level_fees = response["data"]["report"]["paymentLevelFees"]

            report_url = payment_level_fees["url"]
            report = self._retrieve_braintree_report(report_url)
            for transaction in self._braintree_report_to_transactions(report):
                transactions_by_id[transaction.pop("id")].update(transaction)

        lines = list(itertools.chain.from_iterable(map(
            lambda x: self._braintree_transaction_to_lines(x),
            transactions
        )))

        for disbursement_date in disbursement_dates:
            disbursed_transactions = list(filter(
                lambda transaction: (
                    transaction.get("disbursement_date") == disbursement_date
                ),
                transactions
            ))

            disbursed_amount = Decimal()
            for disbursed_transaction in disbursed_transactions:
                # NOTE: This is a bit odd, but disbursement amount is the same
                # as settlement amount, so fees have to be subtracted.
                disbursement_amount = \
                    disbursed_transaction["disbursement_amount"]
                fee_amount = disbursed_transaction["total_fee_amount"]
                disbursed_amount += disbursement_amount - fee_amount

            lines.append({
                "name": _("Disbursement"),
                "amount": str(-disbursed_amount),
                "date": disbursement_date,
                "unique_import_id": "DISBURSEMENT-%s" % (
                    disbursement_date.strftime("%Y%m%d")
                ),
                "note": _("Disbursed transactions: %(TRANSACTIONS)s") % {
                    "TRANSACTIONS": ", ".join([
                        "%(AMOUNT)s %(CURRENCY)s (%(ID)s)" % {
                            "AMOUNT": transaction["presentment_amount"],
                            "CURRENCY": transaction["presentment_currency"],
                            "ID": transaction["id"],
                        }
                        for transaction in disbursed_transactions
                    ])
                },
            })

        lines = list(sorted(
            lines,
            key=lambda transaction: transaction["date"],
        ))

        return lines, {}

    @api.model
    def _braintree_transaction_to_lines(self, transaction):
        if "settlement_date" not in transaction \
                or "settlement_amount" not in transaction:
            return []

        line = {
            "name": _("Transaction %(ACCOUNT)s/%(TRANSACTION)s") % {
                "ACCOUNT": transaction["merchant_account"],
                "TRANSACTION": transaction["id"],
            },
            "amount": str(transaction["settlement_amount"]),
            "date": transaction["settlement_date"],
            "unique_import_id": transaction["id"],
        }
        if "legacy_id" in transaction:
            line.update({
                "note": _("Legacy ID: %(ID)s") % {
                    "ID": transaction["legacy_id"],
                }
            })

        presentment_currency = transaction["presentment_currency"]
        settlement_currency = transaction["settlement_currency"]
        if presentment_currency != settlement_currency \
                and transaction["presentment_amount"]:
            presentment_currency = self.env["res.currency"].search(
                [("name", "=", presentment_currency)],
                limit=1,
            )
            if presentment_currency:
                line.update({
                    "amount_currency": str(transaction["presentment_amount"]),
                    "currency_id": presentment_currency.id,
                })

        return [line, {
            "name": _("Transaction Fees"),
            "amount": str(-transaction["total_fee_amount"]),
            "date": transaction["settlement_date"],
            "unique_import_id": "%s-TOTALFEE" % transaction["id"],
            "note": _("Transaction fees for %(ACCOUNT)s/%(TRANSACTION)s") % {
                "ACCOUNT": transaction["merchant_account"],
                "TRANSACTION": transaction["id"],
            },
        }]

    @api.model
    def _get_braintree_credentials(self, username, password):
        credentials = "%s:%s" % (username, password)
        credentials = b64encode(credentials.encode("utf-8"))
        credentials = str(credentials, "utf-8")
        return credentials

    @api.model
    def _braintree_query(self, credentials, api_base, query, **kwargs):
        data = json.dumps({
            "query": query,
            "variables": kwargs or {},
        })
        with self._braintree_urlopen(credentials, api_base, data=data) as response:
            content = response.read().decode(
                response.headers.get_content_charset() or "utf-8"
            )
        content = json.loads(
            content,
            parse_float=Decimal,
        )
        return content

    @api.model
    def _validate_braintree_response(self, response, except_classes=None):
        if "errors" not in response:
            return response
        if except_classes is not None:
            error_classes = set([
                error["extensions"]["errorClass"]
                for error in response["errors"]
                if "errorClass" in error.get("extensions", {})
            ])
            if not error_classes.difference(except_classes):
                return response
        raise UserError(_("Unexpected response: %s" % (
            "; ".join(map(lambda error: error["message"], response["errors"])),
        )))

    @api.model
    def _braintree_urlopen(self, credentials, url, data=None):
        request = urllib.request.Request(url)
        request.add_header("Authorization", "Basic %s" % credentials)
        request.add_header("Braintree-Version", "2019-01-01")
        if data is not None:
            request.add_header("Content-Type", "application/json")
            if isinstance(data, str):
                data = data.encode("utf-8")
            request.add_header("Content-Length", len(data))
        return urllib.request.urlopen(request, data=data)

    @api.model
    def _retrieve_braintree_report(self, report_url):
        request = urllib.request.Request(report_url)
        with urllib.request.urlopen(request) as response:
            content = response.read().decode(
                response.headers.get_content_charset() or "utf-8"
            )
        return content

    @api.model
    def _braintree_report_to_transactions(self, report):
        report_csv = CsvReader(StringIO(report))

        report_header = list(next(report_csv))
        transaction_id_index = report_header.index("Transaction ID")
        merchant_account_index = report_header.index("Merchant Account ID")
        settlement_date_index = report_header.index("Settlement Date")
        settlement_currency_index = report_header.index("Settlement Currency")
        settlement_amount_index = report_header.index("Settlement Amount")
        total_fee_amount_index = report_header.index("Total Fee Amount")

        transactions = []
        for report_line in report_csv:
            transaction_id = report_line[transaction_id_index]
            merchant_account = report_line[merchant_account_index]
            settlement_date = report_line[settlement_date_index]
            settlement_currency = report_line[settlement_currency_index]
            settlement_amount = report_line[settlement_amount_index]
            total_fee_amount = report_line[total_fee_amount_index]

            transactions.append({
                "id": transaction_id,
                "merchant_account": merchant_account,
                "settlement_date": datetime.strptime(
                    settlement_date,
                    "%Y-%m-%d"
                ).date(),
                "settlement_currency": settlement_currency,
                "settlement_amount": self._parse_decimal(settlement_amount),
                "total_fee_amount": self._parse_decimal(total_fee_amount),
            })

        return transactions

    @api.model
    def _parse_decimal(self, value, currency=None):
        if not value:
            return Decimal()
        value_decimal_part = value[
            -(currency.decimal_places + 1 if currency else len(value)):
        ]
        comma_index = value_decimal_part.rfind(",")
        dot_index = value_decimal_part.rfind(".")
        if comma_index > dot_index:
            decimal_separator = ","
            thousands_separator = "."
        else:
            decimal_separator = "."
            thousands_separator = ","
        value = value.replace(thousands_separator, "")
        if decimal_separator != ".":
            value = value.replace(decimal_separator, ".")
        return Decimal(value)
