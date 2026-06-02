# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest.mock import patch

from odoo.tests.common import SavepointCase


class TestOnlineBankStatementProviderStripe(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # currency_id on the provider is a related field (journal_id.currency_id),
        # so we set USD on the journal directly.
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BNKST",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "password": "test_api_key",
                "journal_id": cls.journal.id,
                "stripe_note": "Custom Note {source.object}",
                "stripe_fee_note": "Fee Note {source.object}",
            }
        )

    def test_obtain_statement_data_success(self):
        mock_stripe_data = [
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
        ]
        patch_path = (
            "odoo.addons.account_bank_statement_import_online_stripe"
            ".models.online_bank_statement_provider_stripe"
            ".OnlineBankStatementProviderStripe._stripe_api_get_all"
        )
        with patch(patch_path, return_value=iter(mock_stripe_data)):
            date_since = datetime(2023, 3, 15)
            date_until = datetime(2023, 3, 17)
            statement_data, statement_values = self.provider._obtain_statement_data(
                date_since, date_until
            )

        # 2 transactions × (1 main line + 1 fee line) = 4 lines
        self.assertEqual(len(statement_data), 4)
        self.assertEqual(statement_values, {})

        # First transaction — main line
        line0 = statement_data[0]
        self.assertEqual(line0["amount"], 100.0)
        self.assertEqual(line0["unique_import_id"], "txn_123")
        self.assertEqual(line0["name"], "stripe INV-001 charge ch_123 card")
        self.assertEqual(line0["note"], "Custom Note charge")
        self.assertEqual(line0["ref"], "INV-001")

        # First transaction — fee line
        line1 = statement_data[1]
        self.assertEqual(line1["amount"], -1.0)
        self.assertEqual(line1["unique_import_id"], "txn_123_fee")
        self.assertEqual(line1["name"], "stripe fee INV-001 charge ch_123 card")
        self.assertEqual(line1["note"], "Fee Note charge")
        self.assertEqual(line1["ref"], "")

        # Second transaction — main line
        line2 = statement_data[2]
        self.assertEqual(line2["amount"], 200.0)
        self.assertEqual(line2["unique_import_id"], "txn_456")
        self.assertEqual(line2["name"], "stripe INV-002 charge ch_456 card")
        self.assertEqual(line2["note"], "Custom Note charge")
        self.assertEqual(line2["ref"], "INV-002")

        # Second transaction — fee line
        line3 = statement_data[3]
        self.assertEqual(line3["amount"], -2.0)
        self.assertEqual(line3["unique_import_id"], "txn_456_fee")
        self.assertEqual(line3["name"], "stripe fee INV-002 charge ch_456 card")
        self.assertEqual(line3["note"], "Fee Note charge")
        self.assertEqual(line3["ref"], "")

    def test_obtain_statement_data_currency_filter(self):
        """Transactions in a different currency are silently skipped."""
        mock_stripe_data = [
            {
                "id": "txn_eur",
                "amount": 5000,
                "currency": "eur",
                "created": 1678886400,
                "object": "balance_transaction",
                "fee": 0,
                "source": {},
            },
        ]
        patch_path = (
            "odoo.addons.account_bank_statement_import_online_stripe"
            ".models.online_bank_statement_provider_stripe"
            ".OnlineBankStatementProviderStripe._stripe_api_get_all"
        )
        with patch(patch_path, return_value=iter(mock_stripe_data)):
            lines, _ = self.provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 17)
            )
        self.assertEqual(lines, [])

    def test_obtain_statement_data_no_fee(self):
        """Transactions with zero fee produce a single line."""
        mock_stripe_data = [
            {
                "id": "txn_nofee",
                "amount": 3000,
                "currency": "usd",
                "created": 1678886400,
                "object": "balance_transaction",
                "fee": 0,
                "source": {},
            },
        ]
        patch_path = (
            "odoo.addons.account_bank_statement_import_online_stripe"
            ".models.online_bank_statement_provider_stripe"
            ".OnlineBankStatementProviderStripe._stripe_api_get_all"
        )
        with patch(patch_path, return_value=iter(mock_stripe_data)):
            lines, _ = self.provider._obtain_statement_data(
                datetime(2023, 3, 15), datetime(2023, 3, 17)
            )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["amount"], 30.0)
        self.assertEqual(lines[0]["unique_import_id"], "txn_nofee")

    def test_safe_format_missing_key(self):
        """_safe_format returns empty string for missing nested paths."""
        from odoo.addons.account_bank_statement_import_online_stripe.models.\
            online_bank_statement_provider_stripe import _safe_format

        result = _safe_format("{missing.key}", {"other": "value"})
        self.assertEqual(result, "")

    def test_safe_format_nested(self):
        from odoo.addons.account_bank_statement_import_online_stripe.models.\
            online_bank_statement_provider_stripe import _safe_format

        result = _safe_format(
            "{a.b.c}",
            {"a": {"b": {"c": "found"}}},
        )
        self.assertEqual(result, "found")

    def test_service_registered(self):
        """The stripe service must appear in the available services list."""
        services = dict(
            self.env["online.bank.statement.provider"]._get_available_services()
        )
        self.assertIn("stripe", services)
        self.assertEqual(services["stripe"], "Stripe")
