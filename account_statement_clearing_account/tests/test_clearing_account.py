# Copyright 2017 Opener BV <https://opener.amsterdam>
# Copyright 2020 Vanmoof BV <https://www.vanmoof.com>
# Copyright 2015-2023 Therp BV <https://therp.nl>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tests.common import TransactionCase


class TestClearingAccount(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.suspense_account = cls.env["account.account"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "TEST Bank Suspense Account",
                "code": "TESTSPS",
                "account_type": "asset_current",
                "reconcile": True,
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "Clearing account test",
                "code": "CAT",
                "type": "bank",
                "bank_acc_number": "NL02ABNA0123456789",
                "currency_id": cls.env.ref("base.USD").id,
                "suspense_account_id": cls.suspense_account.id,
            }
        )
        cls.partner_customer = cls.env["res.partner"].create({"name": "customer"})
        cls.partner_provider = cls.env["res.partner"].create({"name": "provider"})

    def test_reconcile_unreconcile(self):
        """Test that a bank statement that satisfies the conditions, can be
        automatically reconciled.
        """
        # TODO bank statement no longer has a state, nor a confirm button.
        # So the previuously existing checks might need to be done in another way.
        statement = self.env["account.bank.statement"].create(
            {
                "name": "Test autoreconcile 2021-03-08",
                "reference": "AUTO-2021-08-03",
                "date": "2021-03-08",
                "journal_id": self.journal.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "web sale",
                            "journal_id": self.journal.id,
                            "partner_id": self.partner_customer.id,
                            "amount": 100.00,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "transaction_fees",
                            "journal_id": self.journal.id,
                            "partner_id": False,
                            "amount": -1.25,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "due_from_provider",
                            "journal_id": self.journal.id,
                            "partner_id": self.partner_provider.id,
                            "amount": -98.75,
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
        # TODO: Test working of suspend account
        # account = self.env["account.account"].search(
        #     [("account_type", "=", "asset_receivable")], limit=1
        # )
