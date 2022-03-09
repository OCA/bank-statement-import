# Copyright 2021 Therp BV (https://therp.nl).
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from unittest.mock import patch

from odoo.tests import common


class TestAccountJournal(common.TransactionCase):
    """Test some functions adde d to account.journal model."""

    def setUp(self):
        super().setUp()
        self.AccountJournal = self.env["account.journal"]

    def test_values_online_bank_statement_provider(self):
        """Check method to retrieve provider types."""
        # Make sure the users seems to have the group_no_one.
        with patch.object(
            self.AccountJournal.__class__, "user_has_groups", return_value=True
        ):
            values = self.AccountJournal.values_online_bank_statement_provider()
            self.assertIn("dummy", [entry[0] for entry in values])
