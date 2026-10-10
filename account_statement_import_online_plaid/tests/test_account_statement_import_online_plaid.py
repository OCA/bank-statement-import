# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime
from unittest.mock import MagicMock, patch

from odoo.tests import common

TRANSACTIONS = [
    {
        "account_id": "Qxm5dj75QXuBe5QVPAwbIN1PgEMExnCGroLgv",
        "account_owner": None,
        "amount": 500.0,
        "authorized_date": None,
        "authorized_datetime": None,
        "category": ["Food and Drink", "Restaurants"],
        "category_id": "13005000",
        "check_number": None,
        "counterparties": [],
        "date": datetime.date(2024, 6, 20),
        "datetime": None,
        "iso_currency_code": "USD",
        "location": {
            "address": None,
            "city": None,
            "country": None,
            "lat": None,
            "lon": None,
            "postal_code": None,
            "region": None,
            "store_number": None,
        },
        "logo_url": None,
        "merchant_entity_id": None,
        "merchant_name": None,
        "name": "Tectra Inc",
        "payment_channel": "in store",
        "payment_meta": {
            "by_order_of": None,
            "payee": None,
            "payer": None,
            "payment_method": None,
            "payment_processor": None,
            "ppd_id": None,
            "reason": None,
            "reference_number": None,
        },
        "pending": False,
        "pending_transaction_id": None,
        "personal_finance_category": {
            "confidence_level": "LOW",
            "detailed": "ENTERTAINMENT_SPORTING_EVENTS_AMUSEMENT_PARKS_AND_MUSEUMS",
            "primary": "ENTERTAINMENT",
        },
        "transaction_code": None,
        "transaction_id": "Mro5zaR59jCV95J8gNedi4LjoLE76qCL6MMEe",
        "transaction_type": "place",
        "unofficial_currency_code": None,
        "website": None,
    },
    {
        "account_id": "Qxm5dj75QXuBe5QVPAwbIN1PgEMExnCGroLgv",
        "account_owner": None,
        "amount": 30.0,
        "authorized_date": None,
        "authorized_datetime": None,
        "category": ["Food and Drink", "Restaurants"],
        "category_id": "13005000",
        "check_number": None,
        "counterparties": [],
        "date": datetime.date(2024, 5, 7),
        "datetime": None,
        "iso_currency_code": "USD",
        "location": {
            "address": None,
            "city": None,
            "country": None,
            "lat": None,
            "lon": None,
            "postal_code": None,
            "region": None,
            "store_number": None,
        },
        "logo_url": None,
        "merchant_entity_id": None,
        "merchant_name": None,
        "name": "Tectra Inc 2",
        "payment_channel": "in store",
        "payment_meta": {
            "by_order_of": None,
            "payee": None,
            "payer": None,
            "payment_method": None,
            "payment_processor": None,
            "ppd_id": None,
            "reason": None,
            "reference_number": None,
        },
        "pending": False,
        "pending_transaction_id": None,
        "personal_finance_category": {
            "confidence_level": "LOW",
            "detailed": "ENTERTAINMENT_SPORTING_EVENTS_AMUSEMENT_PARKS_AND_MUSEUMS",
            "primary": "ENTERTAINMENT",
        },
        "transaction_code": None,
        "transaction_id": "Mro5zaR59jCV95J8gNedi4LjoLE76qCL6MMEu",
        "transaction_type": "place",
        "unofficial_currency_code": None,
        "website": None,
    },
]

EMPTY_TRANSACTIONS = []


def _make_plaid_transaction(
    transaction_id, amount=250.0, name="TRANSFER TO SAVINGS", **overrides
):
    """Build a minimal Plaid transaction dict with sensible defaults."""
    vals = {
        "account_id": "Qxm5dj75QXuBe5QVPAwbIN1PgEMExnCGroLgv",
        "amount": amount,
        "date": datetime.date(2024, 7, 10),
        "name": name,
        "transaction_id": transaction_id,
        "pending": False,
        "pending_transaction_id": None,
    }
    vals.update(overrides)
    return vals


class TestAccountStatementImportOnlinePlaid(common.TransactionCase):
    post_install = True

    def setUp(self):
        super().setUp()

        self.now = datetime.datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.AccountJournal = self.env["account.journal"]
        self.ResPartnerBank = self.env["res.partner.bank"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]
        self.AccountStatementPull = self.env["online.bank.statement.pull.wizard"]

        self.currency_eur.write({"active": True})

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
                "bank_account_id": self.bank_account.id,
            }
        )
        self.provider = self.OnlineBankStatementProvider.create(
            {
                "name": "plaid Provider",
                "service": "plaid",
                "username": "username",
                "password": "password",
                "plaid_host": "sandbox",
                "plaid_access_token": "access_token",
                "journal_id": self.journal.id,
                # To get all the moves in a month at once
                "statement_creation_mode": "monthly",
            }
        )

    def _pull_statements(self, date_since, date_until):
        """Create and execute a pull wizard for the test journal."""
        wizard = (
            self.env["online.bank.statement.pull.wizard"]
            .with_context(
                active_model="account.journal",
                active_id=self.journal.id,
            )
            .create(
                {
                    "date_since": date_since,
                    "date_until": date_until,
                }
            )
        )
        wizard.action_pull()

    def _get_statement_lines(self):
        return self.AccountBankStatementLine.search(
            [("journal_id", "=", self.journal.id)]
        )

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_import_online_bank_statement_plaid(self, trasactions_get):
        trasactions_get.return_value = {
            "transactions": TRANSACTIONS,
            "total_transactions": len(TRANSACTIONS),
        }
        vals = {
            "date_since": datetime.datetime(2024, 5, 1),
            "date_until": datetime.datetime(2024, 6, 30),
        }
        wizard = (
            self.env["online.bank.statement.pull.wizard"]
            .with_context(
                active_model="account.journal",
                active_id=self.journal.id,
            )
            .create(vals)
        )
        wizard.action_pull()
        statements = self.env["account.bank.statement"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(len(statements), 2)
        lines = statements.line_ids
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0].amount, -500.0)
        self.assertEqual(lines[1].amount, -30.0)

    def test_get_services(self):
        services = self.provider._get_available_services()
        self.assertTrue(services)
        self.assertIn(("plaid", "Plaid.com"), services)

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_pending_to_settled_replaces_line(self, transactions_get):
        """Settled transaction replaces its pending counterpart."""
        pending = _make_plaid_transaction(
            "PENDING_001", pending=True, pending_transaction_id=None
        )
        transactions_get.return_value = {
            "transactions": [pending],
            "total_transactions": 1,
        }
        self._pull_statements(
            datetime.datetime(2024, 7, 1), datetime.datetime(2024, 7, 31)
        )
        lines = self._get_statement_lines()
        self.assertEqual(len(lines), 1, "Pending transaction should be imported")
        pending_line = lines[0]
        self.assertEqual(pending_line.amount, -250.0)

        # Settled version: new transaction_id, pending_transaction_id
        # points back to the original pending ID.
        settled = _make_plaid_transaction(
            "SETTLED_001",
            pending=False,
            pending_transaction_id="PENDING_001",
        )
        transactions_get.return_value = {
            "transactions": [settled],
            "total_transactions": 1,
        }
        self._pull_statements(
            datetime.datetime(2024, 7, 1), datetime.datetime(2024, 7, 31)
        )

        lines = self._get_statement_lines()
        self.assertEqual(
            len(lines),
            1,
            "Settled transaction should replace pending — not create a duplicate",
        )
        self.assertFalse(
            pending_line.exists(), "Pending line's move should have been deleted"
        )

    @patch("plaid.api.plaid_api.PlaidApi.transactions_get")
    def test_settled_dedup_preserves_reconciled(self, transactions_get):
        """A reconciled pending line is kept; the settled one imports alongside."""
        pending = _make_plaid_transaction(
            "PENDING_002", pending=True, pending_transaction_id=None
        )
        transactions_get.return_value = {
            "transactions": [pending],
            "total_transactions": 1,
        }
        self._pull_statements(
            datetime.datetime(2024, 7, 1), datetime.datetime(2024, 7, 31)
        )
        lines = self._get_statement_lines()
        self.assertEqual(len(lines), 1)
        pending_line = lines[0]

        # Reconcile the pending line for real: move its suspense counterpart to
        # a regular account.  `is_reconciled` is a stored computed field that
        # becomes True once `_seek_for_lines()` finds no suspense line left, so
        # this exercises the production code path without patching the ORM.
        counterpart = self.env["account.account"].create(
            {
                "name": "Test Counterpart",
                "code": "TSTCP",
                "account_type": "expense",
            }
        )
        suspense_line = pending_line.move_id.line_ids.filtered(
            lambda line: line.account_id == pending_line.journal_id.suspense_account_id
        )
        suspense_line.account_id = counterpart
        pending_line.invalidate_recordset(["is_reconciled"])
        self.assertTrue(
            pending_line.is_reconciled,
            "Test setup failed: the pending line should now read as reconciled",
        )

        settled = _make_plaid_transaction(
            "SETTLED_002",
            pending=False,
            pending_transaction_id="PENDING_002",
        )
        transactions_get.return_value = {
            "transactions": [settled],
            "total_transactions": 1,
        }
        self._pull_statements(
            datetime.datetime(2024, 7, 1), datetime.datetime(2024, 7, 31)
        )

        lines = self._get_statement_lines()
        self.assertEqual(
            len(lines),
            2,
            "Reconciled pending line must be preserved; settled imports alongside it",
        )
        self.assertTrue(pending_line.exists())

    @patch("plaid.api.plaid_api.PlaidApi.link_token_create")
    def test_action_sycn_with_plaid(self, link_token_create):
        link_token_create.return_value = MagicMock(
            to_dict=lambda: {"link_token": "isalinktoken", "expiration": "isadate"}
        )
        action = self.provider.action_sync_with_plaid()
        self.assertTrue(action)
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "plaid_login")
        self.assertEqual(action["params"]["token"], "isalinktoken")
