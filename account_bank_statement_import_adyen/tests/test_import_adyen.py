# © 2017 Opener BV (<https://opener.amsterdam>)
# © 2020 Vanmoof BV (<https://www.vanmoof.com>)
# © 2015 Therp BV (<http://therp.nl>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
import base64

from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from odoo.tests.common import SavepointCase


class TestImportAdyen(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestImportAdyen, cls).setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "Adyen test",
                "code": "ADY",
                "type": "bank",
                "adyen_merchant_account": "YOURCOMPANY_ACCOUNT",
                "update_posted": True,
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        # Enable reconcilation on the default journal account to trigger
        # the functionality from account_bank_statement_clearing_account
        cls.journal.default_debit_account_id.reconcile = True

    def test_01_import_adyen(self):
        """ Test that the Adyen statement can be imported and that the
        lines on the default journal (clearing) account are fully reconciled
        with each other """
        self._test_statement_import(
            "account_bank_statement_import_adyen",
            "adyen_test.xlsx",
            "YOURCOMPANY_ACCOUNT 2016/48",
        )
        statement = self.env["account.bank.statement"].search(
            [], order="create_date desc", limit=1
        )
        self.assertEqual(statement.journal_id, self.journal)
        self.assertEqual(len(statement.line_ids), 22)
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
        statement.button_draft()
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

    def test_02_import_adyen_credit_fees(self):
        """ Import an Adyen statement with credit fees """
        self._test_statement_import(
            "account_bank_statement_import_adyen",
            "adyen_test_credit_fees.xlsx",
            "YOURCOMPANY_ACCOUNT 2016/8",
        )

    def test_03_import_adyen_invalid(self):
        """ Trying to hit that coverall target """
        with self.assertRaisesRegex(UserError, "Could not make sense"):
            self._test_statement_import(
                "account_bank_statement_import_adyen",
                "adyen_test_invalid.xls",
                "invalid",
            )

    def _test_statement_import(self, module_name, file_name, statement_name):
        """Test correct creation of single statement."""
        statement_path = get_module_resource(module_name, "test_files", file_name)
        statement_file = open(statement_path, "rb").read()
        import_wizard = self.env["account.bank.statement.import"].create(
            {"data_file": base64.b64encode(statement_file), "filename": file_name}
        )
        import_wizard.import_file()
        # statement name is account number + '-' + date of last line:
        statements = self.env["account.bank.statement"].search(
            [("name", "=", statement_name)]
        )
        self.assertTrue(statements)
        return statements
