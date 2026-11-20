# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountBankStatementCascadeDelete(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.company_data["default_journal_bank"]
        cls.statement = cls.env["account.bank.statement"].create(
            {
                "name": "Statement 1",
                "journal_id": cls.journal.id,
                "line_ids": [
                    Command.create(
                        {
                            "payment_ref": "Line 1",
                            "amount": 100.0,
                            "journal_id": cls.journal.id,
                        },
                    )
                ],
            }
        )

    def test_unlink_statement(self):
        self.assertEqual(len(self.statement.line_ids), 1)
        line = self.statement.line_ids[0]
        self.statement.unlink()
        self.assertFalse(self.statement.exists())
        self.assertFalse(line.exists())
