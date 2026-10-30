from datetime import datetime
from unittest.mock import patch

from odoo.tools import mute_logger

from odoo.addons.base.tests.common import BaseCommon

CURRENCY_MODEL = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe"
)


CURRENCY_MODULE = f"{CURRENCY_MODEL}.OnlineBankStatementProviderStripe"


def _currency_transaction(tx_id, amount, currency, source):
    return {
        "id": tx_id,
        "amount": amount,
        "currency": currency,
        "created": 1678886400,
        "object": "balance_transaction",
        "fee": 0,
        "type": "charge",
        "source": source,
    }


CURRENCY_TRANSACTIONS = [
    # A payment of 100.00 USD, settled as 92.00 EUR
    _currency_transaction(
        "txn_usd",
        9200,
        "eur",
        {"id": "ch_1", "object": "charge", "amount": 10000, "currency": "usd"},
    ),
    # A payment of 1000 JPY captured only for 800 JPY, settled as 5.00 EUR
    _currency_transaction(
        "txn_jpy",
        500,
        "eur",
        {
            "id": "ch_2",
            "object": "charge",
            "amount": 1000,
            "amount_captured": 800,
            "currency": "jpy",
        },
    ),
    # A refund of 20.00 USD, settled as -18.40 EUR
    _currency_transaction(
        "txn_refund",
        -1840,
        "eur",
        {"id": "re_1", "object": "refund", "amount": 2000, "currency": "usd"},
    ),
    # A payment in EUR
    _currency_transaction(
        "txn_eur",
        1000,
        "eur",
        {"id": "ch_3", "object": "charge", "amount": 1000, "currency": "eur"},
    ),
    # A transaction of the balance in GBP
    _currency_transaction(
        "txn_gbp",
        700,
        "gbp",
        {"id": "ch_4", "object": "charge", "amount": 700, "currency": "gbp"},
    ),
]


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
        cls.env.ref("base.EUR").active = True
        cls.currency_journal = cls.env["account.journal"].create(
            {
                "name": "Stripe EUR",
                "type": "bank",
                "code": "SCUR",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.EUR").id,
            }
        )
        cls.currency_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.currency_journal.id,
                "stripe_foreign_currency": True,
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

    def _currency_obtain_lines(self):
        with (
            patch(
                f"{CURRENCY_MODULE}._stripe_api_get_all",
                return_value=CURRENCY_TRANSACTIONS,
            ),
            mute_logger(CURRENCY_MODEL),
        ):
            lines, __ = self.currency_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        return {line["unique_import_id"]: line for line in lines}

    def test_foreign_currency(self):
        lines = self._currency_obtain_lines()
        self.assertEqual(lines["txn_usd"]["amount"], 92.0)
        self.assertEqual(
            lines["txn_usd"]["foreign_currency_id"], self.env.ref("base.USD").id
        )
        self.assertEqual(lines["txn_usd"]["amount_currency"], 100.0)
        self.assertEqual(
            lines["txn_jpy"]["foreign_currency_id"], self.env.ref("base.JPY").id
        )
        self.assertEqual(lines["txn_jpy"]["amount_currency"], 800.0)
        self.assertEqual(lines["txn_refund"]["amount_currency"], -20.0)
        self.assertNotIn("foreign_currency_id", lines["txn_eur"])

    def test_foreign_currency_disabled(self):
        self.currency_provider.stripe_foreign_currency = False
        lines = self._currency_obtain_lines()
        self.assertNotIn("foreign_currency_id", lines["txn_usd"])

    def test_other_balance_currency(self):
        lines = self._currency_obtain_lines()
        self.assertNotIn("txn_gbp", lines)
        message = self.currency_provider.message_ids[:1]
        self.assertIn("GBP", message.body)
        # The warning is not repeated at the next pull
        self._currency_obtain_lines()
        self.assertEqual(self.currency_provider.message_ids[:1], message)

    def test_other_balance_currency_with_provider(self):
        """No warning when a provider imports the balance in that currency"""
        self.env.ref("base.GBP").active = True
        journal_gbp = self.env["account.journal"].create(
            {
                "name": "Stripe GBP",
                "type": "bank",
                "code": "STRG",
                "bank_statements_source": "online",
                "currency_id": self.env.ref("base.GBP").id,
            }
        )
        self.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": journal_gbp.id,
            }
        )
        messages = self.currency_provider.message_ids
        self._currency_obtain_lines()
        self.assertEqual(self.currency_provider.message_ids, messages)

    def test_other_balance_currency_of_the_company(self):
        """A journal without currency imports the currency of the company"""
        journal = self.env["account.journal"].create(
            {
                "name": "Stripe company currency",
                "type": "bank",
                "code": "STRC",
                "bank_statements_source": "online",
            }
        )
        self.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": journal.id,
            }
        )
        messages = self.currency_provider.message_ids
        with mute_logger(CURRENCY_MODEL):
            self.currency_provider._stripe_warn_other_currencies(
                {journal.company_id.currency_id.name}
            )
        self.assertEqual(self.currency_provider.message_ids, messages)

    def test_foreign_currency_statement_line(self):
        with patch(
            f"{CURRENCY_MODULE}._stripe_api_get_all",
            return_value=CURRENCY_TRANSACTIONS[:1],
        ):
            self.currency_provider._pull(datetime(2023, 3, 15), datetime(2023, 3, 16))
        line = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.currency_journal.id)]
        )
        self.assertEqual(line.foreign_currency_id, self.env.ref("base.USD"))
        self.assertEqual(line.amount_currency, 100.0)
