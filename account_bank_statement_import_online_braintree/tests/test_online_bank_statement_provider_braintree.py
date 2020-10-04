# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, datetime
import json
from os import path
from unittest import mock

from odoo.tests import common

_MODULE_NS = "odoo.addons.account_bank_statement_import_online_braintree"
_PROVIDER_CLASS = (
    _MODULE_NS
    + ".models.online_bank_statement_provider_braintree"
    + ".OnlineBankStatementProviderBraintree"
)
_RETRIEVE_BRAINTREE_REPORT = _PROVIDER_CLASS + "._retrieve_braintree_report"
_BRAINTREE_QUERY = _PROVIDER_CLASS + "._braintree_query"


class TestOnlineBankStatementProviderBraintree(
    common.TransactionCase
):

    def setUp(self):
        super().setUp()

        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.AccountJournal = self.env["account.journal"]
        self.OnlineBankStatementProvider = self.env[
            "online.bank.statement.provider"
        ]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

    def _data_file(self, filename):
        filepath = path.join(path.dirname(__file__), filename)
        with open(filepath) as file:
            return file.read()

    def _json_file(self, filename):
        return json.loads(self._data_file(filename))

    def test_pull(self):
        journal = self.AccountJournal.create({
            "name": "Bank",
            "type": "bank",
            "code": "BANK",
            "currency_id": self.currency_eur.id,
            "bank_statements_source": "online",
            "online_bank_statement_provider": "braintree",
        })

        provider = journal.online_bank_statement_provider_id
        provider.origin = "usd"
        provider.username = "public_key"
        provider.password = "private_key"

        report = self._data_file("fixtures/pull_report.csv")
        queries = [
            self._json_file("fixtures/pull_query_0.json"),
            self._json_file("fixtures/pull_query_1.json"),
            self._json_file("fixtures/pull_query_2.json"),
        ]
        with mock.patch(_RETRIEVE_BRAINTREE_REPORT, return_value=report), \
                mock.patch(_BRAINTREE_QUERY, side_effect=queries):
            data = provider._obtain_statement_data(
                datetime(2020, 4, 7, 2, 0, 0),
                datetime(2020, 4, 8, 2, 0, 0),
            )

        self.assertEqual(len(data[0]), 5)
        self.assertEqual(data[0][0], {
            "date": date(2020, 4, 6),
            "amount": "993.53",
            "name": "Transaction usd/abcdef0100000000",
            "note": "Legacy ID: abcdef01",
            "unique_import_id": "abcdef0100000000",
            "amount_currency": "1085.00",
            "currency_id": self.currency_usd.id,
        })
        self.assertEqual(data[0][1], {
            "date": date(2020, 4, 6),
            "amount": "-29.10",
            "name": "Transaction Fees",
            "note": "Transaction fees for usd/abcdef0100000000",
            "unique_import_id": "abcdef0100000000-TOTALFEE",
        })
        self.assertEqual(data[0][2], {
            "date": date(2020, 4, 7),
            "amount": "2241.63",
            "name": "Transaction usd/abcdef02",
            "unique_import_id": "abcdef02",
            "amount_currency": "2448.00",
            "currency_id": self.currency_usd.id,
        })
        self.assertEqual(data[0][3], {
            "date": date(2020, 4, 7),
            "amount": "-65.30",
            "name": "Transaction Fees",
            "note": "Transaction fees for usd/abcdef02",
            "unique_import_id": "abcdef02-TOTALFEE",
        })
        self.assertEqual(data[0][4], {
            "date": date(2020, 4, 8),
            "name": "Disbursement",
            "amount": "-3140.76",
            "unique_import_id": "DISBURSEMENT-20200408",
            "note": (
                "Disbursed transactions: 1085.00 USD (abcdef0100000000), " +
                "2448.00 USD (abcdef02)"
            ),
        })

    def test_nodata(self):
        journal = self.AccountJournal.create({
            "name": "Bank",
            "type": "bank",
            "code": "BANK",
            "currency_id": self.currency_eur.id,
            "bank_statements_source": "online",
            "online_bank_statement_provider": "braintree",
        })

        provider = journal.online_bank_statement_provider_id
        provider.origin = "usd"
        provider.username = "public_key"
        provider.password = "private_key"

        query_response = self._json_file("fixtures/nodata_query.json")
        with mock.patch(_BRAINTREE_QUERY, return_value=query_response):
            data = provider._obtain_statement_data(
                datetime(2020, 4, 10, 2, 0, 0),
                datetime(2020, 4, 10, 2, 0, 0),
            )

        self.assertEqual(data, ([], {}))
