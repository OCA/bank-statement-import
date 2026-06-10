# Copyright 2020 Florent de Labarre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from datetime import date, datetime
from unittest import mock

import pytz

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

_module_ns = "odoo.addons.account_statement_import_online_qonto"
_provider_module = _module_ns + ".models.online_bank_statement_provider_qonto"
_provider_class = _provider_module + ".OnlineBankStatementProviderQonto"
_requests_get = _provider_module + ".requests.get"


class TestAccountBankAccountStatementImportOnlineQonto(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.AccountJournal = self.env["account.journal"]
        self.ResPartnerBank = self.env["res.partner.bank"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

        self.bank_account = self.ResPartnerBank.create(
            {
                "acc_number": "FR0214508000302245362775K46",
                "partner_id": self.env.user.company_id.partner_id.id,
            }
        )
        self.journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "qonto",
                "bank_account_id": self.bank_account.id,
            }
        )
        self.provider = self.journal.online_bank_statement_provider_id

        self.mock_slug = lambda: mock.patch(
            _provider_class + "._qonto_get_slug",
            return_value={"FR0214508000302245362775K46": "qonto-1234-bank-account-1"},
        )
        self.mock_transaction = lambda: mock.patch(
            _provider_class + "._qonto_get_transactions",
            return_value={
                "transactions": [
                    {
                        "transaction_id": "qonto-1234-1-transaction-3",
                        "amount": 1200.0,
                        "amount_cents": 120000,
                        "attachment_ids": [],
                        "local_amount": 1200.0,
                        "local_amount_cents": 120000,
                        "side": "credit",
                        "operation_type": "income",
                        "currency": "EUR",
                        "local_currency": "EUR",
                        "label": "INVOICE A",
                        "settled_at": "2020-04-16T07:01:55.503Z",
                        "emitted_at": "2020-04-16T05:01:55.000Z",
                        "updated_at": "2020-04-16T07:04:02.792Z",
                        "status": "completed",
                        "note": None,
                        "reference": "Ref 1233",
                        "vat_amount": None,
                        "vat_amount_cents": None,
                        "vat_rate": None,
                        "initiator_id": None,
                        "label_ids": [],
                        "attachment_lost": False,
                        "attachment_required": True,
                    },
                    {
                        "transaction_id": "qonto-1234-1-transaction-2",
                        "amount": 1128.36,
                        "amount_cents": 112836,
                        "attachment_ids": [],
                        "local_amount": 1128.36,
                        "local_amount_cents": 112836,
                        "side": "debit",
                        "operation_type": "transfer",
                        "currency": "EUR",
                        "local_currency": "EUR",
                        "label": "BILL A",
                        "settled_at": "2020-04-16T07:00:30.979Z",
                        "emitted_at": "2020-04-15T18:22:30.296Z",
                        "updated_at": "2020-04-16T07:03:01.125Z",
                        "status": "completed",
                        "note": None,
                        "reference": "Invoice",
                        "vat_amount": None,
                        "vat_amount_cents": None,
                        "vat_rate": None,
                        "initiator_id": "9b783957-85a6-404a-8320-a298781cb5fa",
                        "label_ids": [],
                        "attachment_lost": False,
                        "attachment_required": True,
                    },
                ],
                "meta": {
                    "current_page": 1,
                    "next_page": None,
                    "prev_page": None,
                    "total_pages": 1,
                    "total_count": 2,
                    "per_page": 100,
                },
            },
        )

    def _get_transaction(self, **kwargs):
        transaction = {
            "transaction_id": "qonto-1234-1-transaction-1",
            "amount": 100.0,
            "local_amount": 100.0,
            "side": "credit",
            "currency": "EUR",
            "local_currency": "EUR",
            "label": "LABEL",
            "settled_at": "2020-04-16T07:01:55.503Z",
            "reference": "REF",
        }
        transaction.update(kwargs)
        return transaction

    def test_01_obtain_statement_data(self):
        # Given: a qonto provider with two mocked transactions (credit/debit).
        with self.mock_transaction(), self.mock_slug():
            # When: statement data is obtained for the period.
            lines, statement_values = self.provider._obtain_statement_data(
                datetime(2020, 4, 15),
                datetime(2020, 4, 17),
            )
        # Then: two statement lines are prepared with expected values.
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0]["payment_ref"], "INVOICE A - Ref 1233")
        self.assertEqual(lines[0]["ref"], "Ref 1233")
        self.assertEqual(lines[0]["amount"], 1200.0)
        self.assertEqual(lines[1]["amount"], -1128.36)

    def test_02_header_no_credentials(self):
        # Given: a provider without username and password.
        # When: the authorization header is built.
        # Then: a UserError is raised.
        with self.assertRaises(UserError):
            self.provider._qonto_header()

    def test_03_header(self):
        # Given: a provider with credentials.
        self.provider.write({"username": "login", "password": "key"})
        # When: the authorization header is built.
        # Then: it contains the login and key.
        self.assertEqual(self.provider._qonto_header(), {"Authorization": "login:key"})

    def test_04_get_slug(self):
        # Given: a provider with credentials and a valid API response.
        self.provider.write({"username": "login", "password": "key"})
        response = mock.Mock(
            status_code=200,
            text=json.dumps(
                {
                    "organization": {
                        "bank_accounts": [
                            {
                                "iban": "FR02 1450 8000 3022 4536 2775 K46",
                                "slug": "qonto-1234-bank-account-1",
                            }
                        ]
                    }
                }
            ),
        )
        # When: slugs are fetched.
        with mock.patch(_requests_get, return_value=response):
            slugs = self.provider._qonto_get_slug()
        # Then: the IBAN is sanitized and mapped to the slug.
        self.assertEqual(
            slugs, {"FR0214508000302245362775K46": "qonto-1234-bank-account-1"}
        )

    def test_05_get_slug_error(self):
        # Given: a provider with credentials and a failing API response.
        self.provider.write({"username": "login", "password": "key"})
        response = mock.Mock(status_code=401, text="Unauthorized")
        # When: slugs are fetched.
        # Then: a UserError is raised.
        with mock.patch(_requests_get, return_value=response):
            with self.assertRaises(UserError):
                self.provider._qonto_get_slug()

    def test_06_get_transactions_error(self):
        # Given: a provider with credentials and a failing API response.
        self.provider.write({"username": "login", "password": "key"})
        response = mock.Mock(status_code=400, text="Bad Request")
        # When: transactions are fetched.
        # Then: a UserError is raised.
        with mock.patch(_requests_get, return_value=response):
            with self.assertRaises(UserError):
                self.provider._qonto_get_transactions("http://test", {})

    def test_07_unknown_account(self):
        # Given: Qonto returns slugs for an IBAN not matching the journal.
        with self.mock_transaction(), mock.patch(
            _provider_class + "._qonto_get_slug",
            return_value={"FR7630001007941234567890185": "qonto-other"},
        ):
            # When: statement data is obtained.
            # Then: a UserError is raised.
            with self.assertRaises(UserError):
                self.provider._obtain_statement_data(
                    datetime(2020, 4, 15),
                    datetime(2020, 4, 17),
                )

    def test_08_no_transactions(self):
        # Given: Qonto returns no transactions for the period.
        with self.mock_slug(), mock.patch(
            _provider_class + "._qonto_get_transactions",
            return_value={"transactions": [], "meta": {"total_pages": 1}},
        ):
            # When: statement data is obtained.
            data = self.provider._obtain_statement_data(
                datetime(2020, 4, 15),
                datetime(2020, 4, 17),
            )
        # Then: no statement data is returned.
        self.assertFalse(data)

    def test_09_pagination(self):
        # Given: Qonto returns transactions split over two pages.
        pages = {
            1: {
                "transactions": [self._get_transaction()],
                "meta": {"total_pages": 2},
            },
            2: {
                "transactions": [
                    self._get_transaction(transaction_id="qonto-1234-1-transaction-2")
                ],
                "meta": {"total_pages": 2},
            },
        }
        # When: transactions are obtained.
        with mock.patch(
            _provider_class + "._qonto_get_transactions",
            side_effect=lambda url, params: pages[params["current_page"]],
        ):
            transactions = self.provider._qonto_obtain_transactions(
                "qonto-1234-bank-account-1",
                datetime(2020, 4, 15),
                datetime(2020, 4, 17),
            )
        # Then: transactions from all pages are collected.
        self.assertEqual(len(transactions), 2)

    def test_10_cross_year(self):
        # Given: a date range spanning two different years.
        captured = {}

        def _capture(url, params):
            captured.update(params)
            return {"transactions": [], "meta": {"total_pages": 1}}

        # When: transactions are obtained.
        with mock.patch(
            _provider_class + "._qonto_get_transactions", side_effect=_capture
        ):
            self.provider._qonto_obtain_transactions(
                "qonto-1234-bank-account-1",
                datetime(2019, 12, 30),
                datetime(2020, 1, 5),
            )
        # Then: the end date is clamped to the last day of the start year.
        self.assertEqual(captured["settled_at_from"], "2019-12-30T00:00:00Z")
        self.assertEqual(captured["settled_at_to"], "2019-12-31T23:59:59Z")

    def test_11_no_local_currency(self):
        # Given: a transaction without local currency.
        transaction = self._get_transaction(local_currency=None)
        # When: a statement line is prepared.
        # Then: a UserError is raised.
        with self.assertRaises(UserError):
            self.provider._qonto_prepare_statement_line(
                transaction, 1, self.currency_eur, {"EUR": self.currency_eur.id}
            )

    def test_12_unknown_currency(self):
        # Given: a transaction with a currency not existing in Odoo.
        transaction = self._get_transaction(local_currency="XXX")
        # When: a statement line is prepared.
        # Then: a UserError is raised.
        with self.assertRaises(UserError):
            self.provider._qonto_prepare_statement_line(
                transaction, 1, self.currency_eur, {"EUR": self.currency_eur.id}
            )

    def test_13_foreign_currency(self):
        # Given: a debit transaction in a currency different from the journal.
        transaction = self._get_transaction(
            local_currency="USD", local_amount=120.0, side="debit"
        )
        # When: a statement line is prepared.
        vals_line = self.provider._qonto_prepare_statement_line(
            transaction,
            1,
            self.currency_eur,
            {"EUR": self.currency_eur.id, "USD": self.currency_usd.id},
        )
        # Then: the line carries the foreign currency and amount.
        self.assertEqual(vals_line["amount"], -100.0)
        self.assertEqual(vals_line["currency_id"], self.currency_usd.id)
        self.assertEqual(vals_line["amount_currency"], -120.0)

    def test_14_get_statement_date(self):
        # Given: a UTC date range.
        # When: the statement date is computed.
        statement_date = self.provider._get_statement_date(
            datetime(2020, 4, 16, 7, 0, tzinfo=pytz.utc),
            datetime(2020, 4, 17, 7, 0, tzinfo=pytz.utc),
        )
        # Then: the date is converted to the Europe/Paris timezone.
        self.assertEqual(statement_date, date(2020, 4, 16))
