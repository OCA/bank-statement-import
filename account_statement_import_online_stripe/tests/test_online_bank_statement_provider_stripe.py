from datetime import datetime, timezone
from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon

BALANCES_MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)


def _balances_ts(*args):
    return int(datetime(*args, tzinfo=timezone.utc).timestamp())


def _balances_transaction(tx_id, created, amount, fee=0, currency="usd"):
    return {
        "id": tx_id,
        "amount": amount,
        "fee": fee,
        "net": amount - fee,
        "currency": currency,
        "created": created,
        "object": "balance_transaction",
        "type": "charge",
        "source": {"id": f"ch_{tx_id}", "object": "charge"},
    }


BALANCES_TRANSACTIONS = [
    _balances_transaction("t0", _balances_ts(2023, 3, 14, 12), 10000),
    _balances_transaction("t1", _balances_ts(2023, 3, 15, 9), 5000, fee=150),
    _balances_transaction("t2", _balances_ts(2023, 3, 15, 18), -2000),
    _balances_transaction("t3", _balances_ts(2023, 3, 16, 10), 1000),
    _balances_transaction("eur", _balances_ts(2023, 3, 15, 10), 99999, currency="eur"),
]


BALANCES_BALANCE = {
    "available": [{"amount": 10000, "currency": "usd"}],
    "pending": [{"amount": 3850, "currency": "usd"}, {"amount": 5, "currency": "eur"}],
}


def _balances_api_get_all(provider, path, params=None):
    params = dict(params or [])
    since = params.get("created[gte]", 0)
    until = params.get("created[lt]", float("inf"))
    return [tx for tx in BALANCES_TRANSACTIONS if since <= tx["created"] < until]


class TestOnlineBankStatementProviderStripe(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "name": "Test Stripe Provider",
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.journal.id,
                "currency_id": cls.env.ref("base.USD").id,
                "stripe_note": "Custom Note {source.object}",
                "stripe_fee_note": "Fee Note {source.object}",
            }
        )
        cls.balances_journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "SBAL",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.balances_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.balances_journal.id,
                "stripe_statement_balances": True,
                "tz": "UTC",
            }
        )

    def test_obtain_statement_data_success(self):
        mock_stripe_data = {
            "data": [
                {
                    "id": "txn_123",
                    "amount": 10000,
                    "currency": "usd",
                    "created": 1678886400,
                    "object": "balance_transaction",
                    "fee": 100,
                    "type": "transfer",
                    "source": {
                        "id": "ch_123",
                        "object": "charge",
                        "metadata": {"invoice_number": "INV-001"},
                        "payment_method_details": {"type": "card"},
                    },
                },
                {
                    "id": "txn_456",
                    "amount": 20000,
                    "currency": "usd",
                    "created": 1678972800,
                    "object": "balance_transaction",
                    "fee": 200,
                    "type": "transfer",
                    "source": {
                        "id": "ch_456",
                        "object": "charge",
                        "metadata": {"invoice_number": "INV-002"},
                        "payment_method_details": {"type": "card"},
                    },
                },
            ],
            "has_more": False,
        }
        with patch(
            "odoo.addons.account_statement_import_online_stripe.models.online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe._stripe_api_get_all",
            return_value=mock_stripe_data["data"],
        ) as mock_get_all:
            date_since = datetime(2023, 3, 15)
            date_until = datetime(2023, 3, 17)
            statement_data, _ = self.provider._obtain_statement_data(
                date_since, date_until
            )
            mock_get_all.assert_called_once()
            self.assertEqual(len(statement_data), 4)
            self.assertEqual(statement_data[0]["amount"], 100.0)
            self.assertEqual(statement_data[0]["unique_import_id"], "txn_123")
            self.assertEqual(statement_data[0]["ref"], "INV-001")
            self.assertEqual(
                statement_data[0]["payment_ref"], "stripe INV-001 charge ch_123 card"
            )
            self.assertEqual(statement_data[0]["narration"], "Custom Note charge")
            self.assertEqual(statement_data[1]["amount"], -1.0)
            self.assertEqual(statement_data[1]["unique_import_id"], "txn_123_fee")
            self.assertEqual(statement_data[1]["ref"], "")
            self.assertEqual(
                statement_data[1]["payment_ref"],
                "stripe fee INV-001 charge ch_123 card",
            )
            self.assertEqual(statement_data[1]["narration"], "Fee Note charge")
            self.assertEqual(statement_data[2]["amount"], 200.0)
            self.assertEqual(statement_data[2]["unique_import_id"], "txn_456")
            self.assertEqual(statement_data[2]["ref"], "INV-002")
            self.assertEqual(
                statement_data[2]["payment_ref"], "stripe INV-002 charge ch_456 card"
            )
            self.assertEqual(statement_data[2]["narration"], "Custom Note charge")
            self.assertEqual(statement_data[3]["amount"], -2.0)
            self.assertEqual(statement_data[3]["unique_import_id"], "txn_456_fee")
            self.assertEqual(statement_data[3]["ref"], "")
            self.assertEqual(
                statement_data[3]["payment_ref"],
                "stripe fee INV-002 charge ch_456 card",
            )
            self.assertEqual(statement_data[3]["narration"], "Fee Note charge")

    def _balances_patches(self):
        return (
            patch(f"{BALANCES_MODULE}._stripe_api_get_all", _balances_api_get_all),
            patch(f"{BALANCES_MODULE}._stripe_api_get", return_value=BALANCES_BALANCE),
        )

    def test_balances_of_a_period(self):
        get_all, get = self._balances_patches()
        with get_all, get:
            __, statement_values = self.balances_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        # Before the 15th only t0; at its end t0, t1 and t2
        self.assertEqual(
            statement_values, {"balance_start": 100.0, "balance_end_real": 128.5}
        )

    def test_balances_of_the_statements(self):
        get_all, get = self._balances_patches()
        with get_all, get as balance:
            self.balances_provider._pull(datetime(2023, 3, 15), datetime(2023, 3, 17))
        statements = self.env["account.bank.statement"].search(
            [("journal_id", "=", self.balances_journal.id)], order="name"
        )
        self.assertEqual(statements.mapped("balance_start"), [100.0, 128.5])
        self.assertEqual(statements.mapped("balance_end_real"), [128.5, 138.5])
        self.assertTrue(all(statements.mapped("is_valid")))
        # The balance is read once for the whole pull
        self.assertEqual(balance.call_count, 1)

    def test_balances_disabled(self):
        self.balances_provider.stripe_statement_balances = False
        get_all, get = self._balances_patches()
        with get_all, get as balance:
            __, statement_values = self.balances_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        self.assertEqual(statement_values, {})
        balance.assert_not_called()
