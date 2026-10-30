from datetime import date, datetime
from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon

DETAILS_MODULE = (
    "odoo.addons.account_statement_import_online_stripe.models"
    ".online_bank_statement_provider_stripe.OnlineBankStatementProviderStripe"
)


def _details_transaction(source, **values):
    return {
        "id": "txn_1",
        "amount": 1000,
        "currency": "usd",
        "created": 1678886400,
        "object": "balance_transaction",
        "fee": 30,
        "type": "charge",
        "source": source,
        **values,
    }


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
        journal = cls.env["account.journal"].create(
            {
                "name": "Stripe",
                "type": "bank",
                "code": "SDET",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.details_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": journal.id,
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

    def _details_obtain_lines(self, transactions):
        with patch(f"{DETAILS_MODULE}._stripe_api_get_all", return_value=transactions):
            lines, __ = self.details_provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 16)
            )
        return lines

    def test_charge_details(self):
        charge = {
            "id": "ch_1",
            "object": "charge",
            "livemode": True,
            "customer": "cus_1",
            "payment_intent": "pi_1",
            "billing_details": {
                "email": "jane@example.com",
                "phone": "+39 0541 000000",
                "address": {
                    "line1": "Via Roma 1",
                    "line2": "Scala B",
                    "postal_code": "47921",
                    "city": "Rimini",
                    "state": "RN",
                    "country": "it",
                },
            },
            "payment_method_details": {
                "type": "card",
                "card": {"last4": "4242", "exp_month": 2, "exp_year": 2028},
            },
        }
        payment_line, fee_line = self._details_obtain_lines(
            [_details_transaction(charge, subscription={"id": "sub_1"})]
        )
        self.assertEqual(payment_line["partner_email"], "jane@example.com")
        self.assertEqual(payment_line["partner_phone"], "+39 0541 000000")
        self.assertEqual(payment_line["partner_street"], "Via Roma 1, Scala B")
        self.assertEqual(payment_line["partner_zip"], "47921")
        self.assertEqual(payment_line["partner_city"], "Rimini")
        self.assertEqual(payment_line["partner_state_name"], "RN")
        self.assertEqual(payment_line["partner_country_id"], self.env.ref("base.it").id)
        self.assertEqual(payment_line["partner_external_ref"], "cus_1")
        self.assertEqual(payment_line["payment_method_type"], "card")
        self.assertEqual(payment_line["card_masked_number"], "**** 4242")
        self.assertEqual(payment_line["card_expiry_date"], date(2028, 2, 29))
        self.assertEqual(payment_line["subscription_ref"], "sub_1")
        self.assertEqual(
            payment_line["provider_url"], "https://dashboard.stripe.com/payments/pi_1"
        )
        self.assertNotIn("partner_email", fee_line)

    def test_payout_details(self):
        payout = {"id": "po_1", "object": "payout", "livemode": False}
        line = self._details_obtain_lines([_details_transaction(payout, fee=0)])[0]
        self.assertEqual(
            line["provider_url"], "https://dashboard.stripe.com/test/payouts/po_1"
        )
        self.assertNotIn("partner_email", line)

    def test_source_not_expanded(self):
        line = self._details_obtain_lines([_details_transaction("ch_1", fee=0)])[0]
        self.assertNotIn("provider_url", line)

    def test_details_on_statement_line(self):
        charge = {
            "id": "ch_1",
            "object": "charge",
            "billing_details": {"email": "jane@example.com"},
        }
        with patch(
            f"{DETAILS_MODULE}._stripe_api_get_all",
            return_value=[_details_transaction(charge, fee=0)],
        ):
            self.details_provider._pull(datetime(2023, 3, 15), datetime(2023, 3, 16))
        line = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.details_provider.journal_id.id)]
        )
        self.assertEqual(line.partner_email, "jane@example.com")
        self.assertEqual(line.transaction_details["source"]["id"], "ch_1")
