# Copyright 2021-2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Test online Adyen reusing tests for manual import."""
from dateutil.relativedelta import relativedelta

from odoo import fields

# pylint: disable=import-error
from odoo.addons.account_bank_statement_import_adyen.tests.test_import_adyen import (
    TestImportAdyen,
)


class TestImportOnline(TestImportAdyen):
    """Do the same tests as with the offline adyen import."""

    @classmethod
    def setUpClass(cls):
        """Setup online journal."""
        # pylint: disable=invalid-name
        super().setUpClass()
        cls.now = fields.Datetime.now()
        cls.journal.write(
            {
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy_adyen",
            }
        )

    def test_03_import_adyen_invalid(self):
        """Override super test: online module test will return without statements."""
        with self.assertRaisesRegex(AssertionError, "account.bank.statement()"):
            self._test_statement_import(
                "adyen_test_invalid.xls", "invalid",
            )

    def _test_statement_import(self, file_name, statement_name):
        """Test correct creation of single statement.

        Getting an adyen statement online should result in:
            1. A valid imported statement;
            2. An incremented batch number;
            3. The current date being set as the date_since in the provider.
        """
        provider = self.journal.online_bank_statement_provider_id
        provider.write(
            {
                "api_base": (
                    "https://ca-test.adyen.com/reports/download/MerchantAccount"
                ),
                "download_file_name": file_name,
                "interval_type": "days",
                "interval_number": 1,
                "service": "dummy_adyen",
                "next_batch_number": 1,
            }
        )
        # Pull from yesterday, until today
        yesterday = self.now - relativedelta(days=1)
        # pylint: disable=protected-access
        provider.with_context(scheduled=True)._pull(yesterday, self.now)
        # statement name is account number + '-' + date of last line.
        statements = self.env["account.bank.statement"].search(
            [("name", "=", statement_name)]
        )
        self.assertTrue(statements)
        self.assertEqual(len(statements), 1)
        self.assertEqual(provider.next_batch_number, 2)
        self.assertEqual(provider.last_successful_run, self.now)
        self.assertTrue(provider.next_run > self.now)
        return statements
