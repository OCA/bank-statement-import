# Copyright 2017 Opener BV <https://opener.amsterdam>
# Copyright 2020 Vanmoof BV <https://www.vanmoof.com>
# Copyright 2015-2021 Therp BV <https://therp.nl>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import SavepointCase


class TestClearingAccount(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "Clearing account test",
                "code": "CAT",
                "type": "bank",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.partner_customer = cls.env["res.partner"].create({"name": "cutomer"})
        cls.partner_provider = cls.env["res.partner"].create({"name": "provider"})
        # Enable reconcilation on the default journal account to trigger
        # the functionality from account_bank_statement_clearing_account
        cls.journal.default_debit_account_id.reconcile = True

    def test_reconcile_unreconcile(self):
        """Test that a bank statement that satiesfies the conditions, cab be
        automatically reconciled and unreconciled on confirmation or reset of the
        statement.
        """
        account = self.journal.default_debit_account_id
        statement = self.env["account.bank.statement"].create(
            {
                "name": "Test autoreconcile 2021-03-08",
                "reference": "AUTO-2021-08-03",
                "date": "2021-03-08",
                "state": "open",
                "journal_id": self.journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "web sale",
                            "partner_id": self.partner_customer.id,
                            "amount": 100.00,
                            "account_id": account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "transaction_fees",
                            "partner_id": False,
                            "amount": -1.25,
                            "account_id": account.id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "due_from_provider",
                            "partner_id": self.partner_provider.id,
                            "amount": -98.75,
                            "account_id": account.id,
                        },
                    ),
                ],
            }
        )
        self.assertEqual(statement.journal_id, self.journal)
        self.assertEqual(len(statement.line_ids), 3)
        self.assertTrue(
            self.env.user.company_id.currency_id.is_zero(
                sum(line.amount for line in statement.line_ids)
            )
        )
        account = self.env["account.account"].search(
            [("internal_type", "=", "receivable")], limit=1
        )
        for line in statement.line_ids:
            line.process_reconciliation(
                new_aml_dicts=[
                    {
                        "debit": -line.amount if line.amount < 0 else 0,
                        "credit": line.amount if line.amount > 0 else 0,
                        "account_id": account.id,
                    }
                ]
            )
        statement.button_confirm_bank()
        self.assertEqual(statement.state, "confirm")
        lines = self.env["account.move.line"].search(
            [
                ("account_id", "=", self.journal.default_debit_account_id.id),
                ("statement_id", "=", statement.id),
            ]
        )
        reconcile = lines.mapped("full_reconcile_id")
        self.assertEqual(len(reconcile), 1)
        self.assertEqual(lines, reconcile.reconciled_line_ids)

        # Reset the bank statement to see the counterpart lines being
        # unreconciled
        statement.button_reopen()
        self.assertEqual(statement.state, "open")
        self.assertFalse(lines.mapped("matched_debit_ids"))
        self.assertFalse(lines.mapped("matched_credit_ids"))
        self.assertFalse(lines.mapped("full_reconcile_id"))

        # Confirm the statement without the correct clearing account settings
        self.journal.default_debit_account_id.reconcile = False
        statement.button_confirm_bank()
        self.assertEqual(statement.state, "confirm")
        self.assertFalse(lines.mapped("matched_debit_ids"))
        self.assertFalse(lines.mapped("matched_credit_ids"))
        self.assertFalse(lines.mapped("full_reconcile_id"))
