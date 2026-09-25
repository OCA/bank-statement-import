from pathlib import Path
from runpy import run_path

from odoo.addons.base.tests.common import BaseCommon


class TestStripeLabelMigration(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        journal = cls.env["account.journal"].create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "stripe",
                "journal_id": journal.id,
            }
        )

    def test_migration_updates_only_default_stripe_label(self):
        old_label = (
            "stripe {source.metadata.invoice_number} {source.object} "
            "{source.id} {source.payment_method_details.type}"
        )
        new_label = (
            "stripe {source.metadata.invoice_number} {source.payment_intent} "
            "{source.object} {source.id} {source.payment_method_details.type}"
        )
        migration_path = (
            Path(__file__).parents[1]
            / "migrations"
            / "18.0.1.1.0"
            / "post-migration.py"
        )
        migrate = run_path(str(migration_path))["migrate"]

        self.provider.stripe_label = old_label
        self.provider.flush_recordset(["stripe_label"])
        migrate(self.env.cr, "18.0.1.0.1")
        self.provider.invalidate_recordset(["stripe_label"])
        self.assertEqual(self.provider.stripe_label, new_label)

        custom_label = "Custom Stripe label"
        self.provider.stripe_label = custom_label
        self.provider.flush_recordset(["stripe_label"])
        migrate(self.env.cr, "18.0.1.0.1")
        self.provider.invalidate_recordset(["stripe_label"])
        self.assertEqual(self.provider.stripe_label, custom_label)
