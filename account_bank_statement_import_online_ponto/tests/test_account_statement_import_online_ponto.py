# Copyright 2020 Florent de Labarre
# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging
from datetime import date, datetime
from unittest import mock

from odoo import _, fields
from odoo.tests import Form, common

_logger = logging.getLogger(__name__)

_module_ns = "odoo.addons.account_bank_statement_import_online_ponto"
_interface_class = (
    _module_ns
    + ".models.ponto_interface"
    + ".PontoInterface"
)

# Transactions should be ordered by descending executionDate.
FOUR_TRANSACTIONS = [
    # First transaction will be after date_until.
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
        "id": "1552c32f-e63f-4ce6-a974-f270e6cd53a9",
        "attributes": {
            "valueDate": "2019-12-04T12:30:00.000Z",
            "remittanceInformationType": "unstructured",
            "remittanceInformation": "Arresto Momentum",
            "executionDate": "2019-12-04T10:25:00.000Z",
            "description": "Wire transfer after execution",
            "currency": "EUR",
            "counterpartReference": "XY10312327598696",
            "counterpartName": "Some other customer",
            "amount": 8.95,
        },
    },
    # Next transaction has valueDate before, executionDate after date_until.
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

transaction_amounts = [5.48, 5.83, 6.08, 8.95]


class TestBankAccountStatementImportOnlinePonto(common.TransactionCase):
    post_install = True

    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.AccountJournal = self.env["account.journal"]
        self.ResPartnerBank = self.env["res.partner.bank"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountAccount = self.env["account.account"]
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
        self.receivable_account = self.AccountAccount.create(
            {
                "code": "1325",
                "name": "Test receivable account",
                "user_type_id": self.env.ref("account.data_account_type_payable").id,
                "reconcile": True,
            }
        )
        self.provider = self.journal.online_bank_statement_provider_id
        # To get all the moves in a month at once
        self.provider.statement_creation_mode = "monthly"

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
            side_effect=[FOUR_TRANSACTIONS, EMPTY_TRANSACTIONS, ]
        )

    def test_balance_start(self):
        st_form = Form(self.AccountBankStatement)
        st_form.journal_id = self.journal
        st_form.date = date(2019, 11, 1)
        st_form.balance_end_real = 100
        with st_form.line_ids.new() as line_form:
            line_form.name = "test move"
            line_form.amount = 100
        initial_statement = st_form.save()
        initial_statement.line_ids[0].account_id = self.receivable_account
        initial_statement.button_confirm_bank()
        with self.mock_login(), \
            self.mock_set_access_account(),  \
            self.mock_get_transactions():  # noqa: B950
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

    def test_ponto_execution_date(self):
        with self.mock_login(), \
            self.mock_set_access_account(), \
            self.mock_get_transactions():  # noqa: B950
            # First base selection on execution date.
            self.provider.ponto_date_field = "execution_date"
            statement = self._get_statement_from_wizard()
            self._check_line_count(statement.line_ids, expected_count=2)
            self._check_statement_amounts(statement, transaction_amounts[:2])

    def test_ponto_value_date(self):
        with self.mock_login(), \
            self.mock_set_access_account(), \
            self.mock_get_transactions():  # noqa: B950
            # First base selection on execution date.
            self.provider.ponto_date_field = "value_date"
            statement = self._get_statement_from_wizard()
            self._check_line_count(statement.line_ids, expected_count=3)
            self._check_statement_amounts(statement, transaction_amounts[:3])

    def test_ponto_scheduled(self):
        with self.mock_login(), \
            self.mock_set_access_account(), \
            self.mock_get_transactions():  # noqa: B950
            # Scheduled should get all transaction, ignoring date_until.
            self.provider.ponto_last_identifier = False
            date_since = datetime(2019, 11, 3)
            date_until = datetime(2019, 11, 18)
            self.provider.with_context(scheduled=True)._pull(date_since, date_until)
            statements = self._get_statements_from_journal(expected_count=2)
            self._check_line_count(statements[0].line_ids, expected_count=3)
            self._check_statement_amounts(statements[0], transaction_amounts[:3])
            self._check_line_count(statements[1].line_ids, expected_count=1)
            # Expected balance_end will include amounts of previous statement.
            self._check_statement_amounts(
                statements[1], transaction_amounts[3:], expected_balance_end=26.34
            )

    def test_ponto_scheduled_from_identifier(self):
        with self.mock_login(), \
            self.mock_set_access_account(), \
            self.mock_get_transactions():  # noqa: B950
            # Scheduled should get all transactions after last identifier.
            self.provider.ponto_last_identifier = "9ac50483-16dc-4a82-aa60-df56077405cd"
            date_since = datetime(2019, 11, 3)
            date_until = datetime(2019, 11, 18)
            self.provider.with_context(scheduled=True)._pull(date_since, date_until)
            # First two transactions for statement 0 should have been ignored.
            statements = self._get_statements_from_journal(expected_count=2)
            self._check_line_count(statements[0].line_ids, expected_count=1)
            self._check_statement_amounts(statements[0], transaction_amounts[2:3])
            self._check_line_count(statements[1].line_ids, expected_count=1)
            # Expected balance_end will include amounts of previous statement.
            self._check_statement_amounts(
                statements[1], transaction_amounts[3:], expected_balance_end=15.03
            )

    def _get_statement_from_wizard(self):
        """Run wizard to pull data and return statement."""
        vals = {
            "provider_ids": [(4, self.provider.id)],
            "date_since": datetime(2019, 11, 3),
            "date_until": datetime(2019, 11, 18),
        }
        wizard = self.AccountStatementPull.with_context(
            active_model="account.journal",
            active_id=self.journal.id,
        ).create(vals)
        # For some reason the provider is not set in the create.
        wizard.provider_ids = self.provider
        wizard.action_pull()
        return self._get_statements_from_journal(expected_count=1)

    def _get_statements_from_journal(self, expected_count=0):
        """We only expect statements created by our tests."""
        statements = self.AccountBankStatement.search(
            [("journal_id", "=", self.journal.id)],
            order="date asc",
        )
        self.assertEqual(len(statements), expected_count)
        return statements

    def _check_line_count(self, lines, expected_count=0):
        """Check wether lines contain expected number of transactions.

        If count differs, show the unique id's of lines that are present.
        """
        # If we do not get all lines, show lines we did get:
        line_count = len(lines)
        if line_count != expected_count:
            _logger.info(
                _("Statement contains transactions: %s"),
                " ".join(lines.mapped("unique_import_id")),
            )
        self.assertEqual(line_count, expected_count)

    def _check_statement_amounts(
        self, statement, expected_amounts, expected_balance_end=0.0
    ):
        """Check wether amount in lines and end_balance as expected."""
        sorted_amounts = sorted([round(line.amount, 2) for line in statement.line_ids])
        self.assertEqual(sorted_amounts, expected_amounts)
        if not expected_balance_end:
            expected_balance_end = sum(expected_amounts)
        self.assertEqual(statement.balance_end, expected_balance_end)
