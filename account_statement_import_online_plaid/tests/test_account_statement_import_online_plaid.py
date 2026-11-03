# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import datetime
import json
from unittest.mock import MagicMock, patch

from odoo.exceptions import AccessError, UserError
from odoo.tests import new_test_user, tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


def _transaction(transaction_id, date, amount, name, pending=False, merchant=None):
    return {
        "account_id": "checking",
        "amount": amount,
        "date": date,
        "iso_currency_code": "USD",
        "merchant_name": merchant,
        "name": name,
        "pending": pending,
        "transaction_id": transaction_id,
    }


TRANSACTIONS = [
    _transaction(
        "t1", datetime.date(2024, 6, 20), 500.0, "Tectra Inc", merchant="Tectra"
    ),
    _transaction("t2", datetime.date(2024, 5, 7), -30.0, "Refund"),
    _transaction(
        "t3", datetime.date(2024, 6, 21), 12.5, "Pending charge", pending=True
    ),
]

ACCOUNTS = [
    {"account_id": "checking", "name": "Checking", "mask": "1111"},
    {"account_id": "card", "name": "Credit Card", "mask": "2222"},
]


@tagged("post_install", "-at_install")
@patch("plaid.api.plaid_api.PlaidApi.transactions_get")
class TestAccountStatementImportOnlinePlaid(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env.company.country_id = cls.env.ref("base.us")
        cls.journal = cls._journal("Checking", "TCHK")
        cls.card_journal = cls._journal("Card", "TCRD")
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "plaid",
                "username": "client_id",
                "password": "secret",
                "plaid_host": "sandbox",
                "plaid_access_token": "access_token",
                "plaid_account_id": "checking",
                "journal_id": cls.journal.id,
                "tz": "America/Chicago",
                # To get all the moves in a month at once
                "statement_creation_mode": "monthly",
            }
        )

    @classmethod
    def _journal(cls, name, code):
        return cls.env["account.journal"].create(
            {
                "name": name,
                "type": "bank",
                "code": code,
                "currency_id": cls.env.ref("base.USD").id,
                "bank_statements_source": "online",
            }
        )

    def _pull(self, journal=None, since=(2024, 5, 1), until=(2024, 6, 30)):
        wizard = (
            self.env["online.bank.statement.pull.wizard"]
            .with_context(
                active_model="account.journal",
                active_id=(journal or self.journal).id,
            )
            .create(
                {
                    "date_since": datetime.datetime(*since),
                    "date_until": datetime.datetime(*until),
                }
            )
        )
        wizard.action_pull()
        return self.env["account.bank.statement.line"].search(
            [("journal_id", "=", (journal or self.journal).id)], order="date"
        )

    def _response(self, transactions=TRANSACTIONS):
        return {"transactions": transactions, "total_transactions": len(transactions)}

    def test_pull(self, transactions_get):
        transactions_get.return_value = self._response()
        lines = self._pull()
        self.assertEqual(len(lines.statement_id), 2)
        # The pending charge is left out.
        self.assertEqual(lines.mapped("payment_ref"), ["Refund", "Tectra Inc"])
        self.assertEqual(lines.mapped("amount"), [30.0, -500.0])
        # Dates are kept as the bank's, not shifted by the timezone.
        self.assertEqual(
            lines.mapped("date"),
            [datetime.date(2024, 5, 7), datetime.date(2024, 6, 20)],
        )
        self.assertEqual(lines[1].partner_name, "Tectra")
        self.assertEqual(json.loads(lines[1].raw_data)["transaction_id"], "t1")

    def test_pull_again_skips_duplicates(self, transactions_get):
        transactions_get.return_value = self._response()
        self._pull()
        self.assertEqual(len(self._pull()), 2)

    def test_one_api_call_per_pull(self, transactions_get):
        transactions_get.return_value = self._response()
        self.provider.statement_creation_mode = "daily"
        lines = self._pull()
        self.assertEqual(transactions_get.call_count, 1)
        self.assertEqual(len(lines), 2)
        request = transactions_get.call_args.args[0]
        self.assertEqual(request.options.account_ids, ["checking"])
        # The pull ends at 2024-06-30 00:00 UTC, which is 6/29 in Chicago, so
        # the last daily statement is 6/29.
        self.assertEqual(request.start_date, datetime.date(2024, 4, 30))
        self.assertEqual(request.end_date, datetime.date(2024, 6, 29))

    def test_monthly_pull_covers_last_month(self, transactions_get):
        transactions_get.return_value = self._response()
        self._pull()
        request = transactions_get.call_args.args[0]
        self.assertEqual(request.end_date, datetime.date(2024, 6, 30))

    def test_scheduled_pull_looks_back(self, transactions_get):
        # A transaction dated 6/20 that posted after the 6/25 pull.
        transactions_get.return_value = self._response(TRANSACTIONS[:1])
        self.provider.statement_creation_mode = "daily"
        since, until = datetime.datetime(2024, 6, 25), datetime.datetime(2024, 6, 26)
        self.provider._pull(since, until)
        self.assertEqual(
            transactions_get.call_args.args[0].start_date, datetime.date(2024, 6, 24)
        )
        lines = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertFalse(lines)
        self.provider.with_context(scheduled=True)._pull(since, until)
        self.assertEqual(
            transactions_get.call_args.args[0].start_date, datetime.date(2024, 6, 11)
        )
        lines = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(lines.payment_ref, "Tectra Inc")

    def test_pull_requires_account(self, transactions_get):
        self.provider.plaid_account_id = False
        with self.assertRaisesRegex(UserError, "Choose Account"):
            self._pull()

    def test_pull_requires_login(self, transactions_get):
        self.provider.plaid_access_token = False
        with self.assertRaisesRegex(UserError, "Link with Plaid"):
            self._pull()

    def test_shared_login(self, transactions_get):
        card = self.env["online.bank.statement.provider"].create(
            {
                "service": "plaid",
                "journal_id": self.card_journal.id,
                "plaid_link_provider_id": self.provider.id,
                "plaid_account_id": "card",
            }
        )
        self.assertTrue(card.plaid_linked)
        transactions_get.return_value = self._response(TRANSACTIONS[:1])
        self.assertEqual(len(self._pull(self.card_journal)), 1)
        request = transactions_get.call_args.args[0]
        self.assertEqual(request.access_token, "access_token")
        self.assertEqual(request.options.account_ids, ["card"])
        with self.assertRaisesRegex(UserError, "uses the Plaid login"):
            card.action_sync_with_plaid()
        with self.assertRaisesRegex(UserError, "share this bank login"):
            self.provider.action_plaid_unlink()

    def test_access_token_admin_only(self, transactions_get):
        user = new_test_user(
            self.env,
            login="plaid_accountant",
            groups="account.group_account_user,account.group_account_manager",
        )
        provider = self.provider.with_user(user)
        with self.assertRaises(AccessError):
            provider.read(["plaid_access_token"])
        self.assertTrue(provider.plaid_linked)
        transactions_get.return_value = self._response()
        provider._pull(datetime.datetime(2024, 5, 1), datetime.datetime(2024, 6, 30))
        lines = self.env["account.bank.statement.line"].with_user(user)
        self.assertEqual(lines.search_count([("journal_id", "=", self.journal.id)]), 2)

    @patch("plaid.api.plaid_api.PlaidApi.accounts_get")
    @patch("plaid.api.plaid_api.PlaidApi.item_public_token_exchange")
    def test_link_single_account(self, exchange, accounts_get, transactions_get):
        self.provider.write({"plaid_access_token": False, "plaid_account_id": False})
        exchange.return_value = {"access_token": "new_token"}
        accounts_get.return_value = {"accounts": ACCOUNTS[:1]}
        result = self.provider.plaid_create_access_token("public", self.provider.id)
        self.assertFalse(result)
        self.assertEqual(self.provider.plaid_access_token, "new_token")
        self.assertEqual(self.provider.plaid_account_id, "checking")
        self.assertEqual(self.provider.plaid_account_name, "Checking ••1111")

    @patch("plaid.api.plaid_api.PlaidApi.accounts_get")
    @patch("plaid.api.plaid_api.PlaidApi.item_public_token_exchange")
    def test_link_several_accounts(self, exchange, accounts_get, transactions_get):
        self.provider.write({"plaid_access_token": False, "plaid_account_id": False})
        exchange.return_value = {"access_token": "new_token"}
        accounts_get.return_value = {"accounts": ACCOUNTS}
        action = self.provider.plaid_create_access_token("public", self.provider.id)
        wizard = self.env[action["res_model"]].browse(action["res_id"])
        self.assertEqual(len(wizard.line_ids), 2)
        wizard.line_id = wizard.line_ids.filtered(
            lambda line: line.plaid_account_id == "card"
        )
        wizard.action_select()
        self.assertEqual(self.provider.plaid_account_id, "card")

    @patch("plaid.api.plaid_api.PlaidApi.item_public_token_exchange")
    def test_reconnect_keeps_login(self, exchange, transactions_get):
        self.assertFalse(
            self.provider.plaid_create_access_token("public", self.provider.id)
        )
        exchange.assert_not_called()
        self.assertEqual(self.provider.plaid_access_token, "access_token")

    @patch("plaid.api.plaid_api.PlaidApi.link_token_create")
    def test_action_sync_with_plaid(self, link_token_create, transactions_get):
        link_token_create.return_value = MagicMock(
            to_dict=lambda: {"link_token": "isalinktoken", "expiration": "isadate"}
        )
        action = self.provider.action_sync_with_plaid()
        self.assertEqual(action["type"], "ir.actions.client")
        self.assertEqual(action["tag"], "plaid_login")
        self.assertEqual(action["params"]["token"], "isalinktoken")
        # Already linked, so Link opens in update mode.
        self.assertEqual(
            link_token_create.call_args.args[0].access_token, "access_token"
        )

    @patch("plaid.api.plaid_api.PlaidApi.item_remove")
    def test_unlink(self, item_remove, transactions_get):
        self.provider.action_plaid_unlink()
        self.assertEqual(item_remove.call_args.args[0].access_token, "access_token")
        self.assertFalse(self.provider.plaid_access_token)
        self.assertFalse(self.provider.plaid_account_id)
        self.assertFalse(self.provider.plaid_linked)

    def test_get_services(self, transactions_get):
        self.assertIn(("plaid", "Plaid.com"), self.provider._get_available_services())
