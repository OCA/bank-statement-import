# Copyright 2020 Florent de Labarre
# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, datetime
from unittest import mock

from odoo import fields
from odoo.tests import Form, common

_module_ns = "odoo.addons.account_statement_import_online_ponto"
_interface_class = _module_ns + ".models.ponto_interface" + ".PontoInterface"

THREE_TRANSACTIONS = [
    {
        "type": "transaction",
        "relationships": {
            "account": {
                "links": {"related": "https://api.myponto.com/accounts/"},
                "data": {
                    "type": "account",
                    "id": "fd3d5b1d-fca9-4310-a5c8-76f2a9dc7c75",
                },
            }
        },
        "id": "701ab965-21c4-46ca-b157-306c0646e0e2",
        "attributes": {
            "valueDate": "2019-11-18T00:00:00.000Z",
            "remittanceInformationType": "unstructured",
            "remittanceInformation": "Minima vitae totam!",
            "executionDate": "2019-11-20T00:00:00.000Z",
            "description": "Wire transfer",
            "currency": "EUR",
            "counterpartReference": "BE26089479973169",
            "counterpartName": "Osinski Group",
            "amount": 6.08,
        },
    },
    {
        "type": "transaction",
        "relationships": {
            "account": {
                "links": {"related": "https://api.myponto.com/accounts/"},
                "data": {
                    "type": "account",
                    "id": "fd3d5b1d-fca9-4310-a5c8-76f2a9dc7c75",
                },
            }
        },
        "id": "9ac50483-16dc-4a82-aa60-df56077405cd",
        "attributes": {
            "valueDate": "2019-11-04T00:00:00.000Z",
            "remittanceInformationType": "unstructured",
            "remittanceInformation": "Quia voluptatem blanditiis.",
            "executionDate": "2019-11-06T00:00:00.000Z",
            "description": "Wire transfer",
            "currency": "EUR",
            "counterpartReference": "BE97201830401438",
            "counterpartName": "Stokes-Miller",
            "amount": 5.48,
        },
    },
    {
        "type": "transaction",
        "relationships": {
            "account": {
                "links": {"related": "https://api.myponto.com/accounts/"},
                "data": {
                    "type": "account",
                    "id": "fd3d5b1d-fca9-4310-a5c8-76f2a9dc7c75",
                },
            }
        },
        "id": "b21a6c65-1c52-4ba6-8cbc-127d2b2d85ff",
        "attributes": {
            "valueDate": "2019-11-04T00:00:00.000Z",
            "remittanceInformationType": "unstructured",
            "remittanceInformation": "Laboriosam repelo?",
            "executionDate": "2019-11-04T00:00:00.000Z",
            "description": "Wire transfer",
            "currency": "EUR",
            "counterpartReference": "BE10325927501996",
            "counterpartName": "Strosin-Veum",
            "amount": 5.83,
        },
    },
]

EMPTY_TRANSACTIONS = []


class TestAccountStatementImportOnlinePonto(common.TransactionCase):
    post_install = True

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
        self.AccountStatementPull = self.env["online.bank.statement.pull.wizard"]

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
                "online_bank_statement_provider": "ponto",
                "bank_account_id": self.bank_account.id,
            }
        )
        self.provider = self.journal.online_bank_statement_provider_id

        self.mock_login = lambda: mock.patch(
            _interface_class + "._login",
            return_value={
                "username": "test_user",
                "password": "very_secret",
                "access_token": "abcd1234",
                "token_expiration": datetime(2099, 12, 31, 23, 59, 59),
            },
        )
        self.mock_set_access_account = lambda: mock.patch(
            _interface_class + "._set_access_account",
            return_value=None,
        )
        # return list of transactions on first call, empty list on second call.
        self.mock_get_transactions = lambda: mock.patch(
            _interface_class + "._get_transactions",
            side_effect=[
                THREE_TRANSACTIONS,
                EMPTY_TRANSACTIONS,
            ],
        )

    def test_balance_start(self):
        st_form = Form(self.AccountBankStatement)
        st_form.journal_id = self.journal
        st_form.date = date(2019, 11, 1)
        st_form.balance_end_real = 100
        with st_form.line_ids.new() as line_form:
            line_form.payment_ref = "test move"
            line_form.amount = 100
        initial_statement = st_form.save()
        initial_statement.button_post()
        with self.mock_login(), self.mock_set_access_account(), self.mock_get_transactions():  # noqa: B950
            vals = {
                "provider_ids": [(4, self.provider.id)],
                "date_since": datetime(2019, 11, 4),
                "date_until": datetime(2019, 11, 5),
            }
            wizard = self.AccountStatementPull.with_context(
                active_model="account.journal",
                active_id=self.journal.id,
            ).create(vals)
            # For some reason the provider is not set in the create.
            wizard.provider_ids = self.provider
            wizard.action_pull()
            statements = self.AccountBankStatement.search(
                [("journal_id", "=", self.journal.id)]
            )
            new_statement = statements - initial_statement
            self.assertEqual(len(new_statement.line_ids), 1)
            self.assertEqual(new_statement.balance_start, 100)
            self.assertEqual(new_statement.balance_end, 105.83)
            # Ponto does not give balance info in transactions.
            # self.assertEqual(new_statement.balance_end_real, 105.83)

    def test_ponto(self):
        with self.mock_login(), self.mock_set_access_account(), self.mock_get_transactions():  # noqa: B950
            vals = {
                "provider_ids": [(4, self.provider.id)],
                "date_since": datetime(2019, 11, 3),
                "date_until": datetime(2019, 11, 17),
            }
            wizard = self.AccountStatementPull.with_context(
                active_model="account.journal",
                active_id=self.journal.id,
            ).create(vals)
            # To get all the moves at once
            self.provider.statement_creation_mode = "monthly"
            # For some reason the provider is not set in the create.
            wizard.provider_ids = self.provider
            wizard.action_pull()
            statement = self.AccountBankStatement.search(
                [("journal_id", "=", self.journal.id)]
            )
            self.assertEqual(len(statement), 1)
            self.assertEqual(len(statement.line_ids), 3)
            sorted_amounts = sorted(statement.line_ids.mapped("amount"))
            self.assertEqual(sorted_amounts, [5.48, 5.83, 6.08])
            self.assertEqual(statement.balance_end, 17.39)
            # Ponto does not give balance info in transactions.
            # self.assertEqual(statement.balance_end_real, 17.39)
