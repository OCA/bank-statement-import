# Copyright 2017 Opener BV <https://opener.amsterdam>
# Copyright 2020 Vanmoof BV <https://www.vanmoof.com>
# Copyright 2015-2022 Therp BV <https://therp.nl>)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Run test imports of Adyen files."""
import base64

from odoo.exceptions import UserError
from odoo.modules.module import get_module_resource
from odoo.tests.common import SavepointCase


class TestImportAdyen(SavepointCase):
    """Run test imports of Adyen files."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "Adyen test",
                "code": "ADY",
                "type": "bank",
                "adyen_merchant_account": "YOURCOMPANY_ACCOUNT",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )

    def test_01_import_adyen(self):
        """ Test that the Adyen statement can be imported and that the
        lines on the default journal (clearing) account are fully reconciled
        with each other """
        self._test_statement_import(
            "adyen_test.xlsx", "YOURCOMPANY_ACCOUNT 2016/48",
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

    def test_02_import_adyen_credit_fees(self):
        """ Import an Adyen statement with credit fees """
        self._test_statement_import(
            "adyen_test_credit_fees.xlsx", "YOURCOMPANY_ACCOUNT 2016/8",
        )

    def test_03_import_adyen_invalid(self):
        """ Trying to hit that coverall target """
        with self.assertRaisesRegex(UserError, "not a Adyen settlement details file"):
            self._test_statement_import(
                "adyen_test_invalid.xls", "invalid",
            )

    def test_04_import_adyen_csv(self):
        """ Test that the Adyen statement can be imported in csv format."""
        self._test_statement_import(
            "settlement_detail_report_batch_380.csv", "YOURCOMPANY_ACCOUNT 2021/380",
        )
        statement = self.env["account.bank.statement"].search(
            [], order="create_date desc", limit=1
        )
        self.assertEqual(statement.journal_id, self.journal)
        # Csv lines has 229 lines. Minus 1 header. Plus 1 extra transaction line.
        self.assertEqual(len(statement.line_ids), 229)
        self.assertTrue(
            self.env.user.company_id.currency_id.is_zero(
                sum(line.amount for line in statement.line_ids)
            )
        )

    def test_05_import_adyen_csv(self):
        """ Test that the Adyen statement without Merchant Payoutcan be imported."""
        self._test_statement_import(
            "settlement_detail_report_batch_238.csv", "YOURCOMPANY_ACCOUNT 2022/238",
        )
        statement = self.env["account.bank.statement"].search(
            [], order="create_date desc", limit=1
        )
        self.assertEqual(statement.journal_id, self.journal)
        # Csv lines has 4 lines. Minus 1 header. No extra transaction line.
        self.assertEqual(len(statement.line_ids), 3)
        self.assertTrue(
            self.env.user.company_id.currency_id.is_zero(
                sum(line.amount for line in statement.line_ids)
            )
        )

    def _test_statement_import(self, file_name, statement_name):
        """Test correct creation of single statement."""
        testfile = get_module_resource(
            "account_bank_statement_import_adyen", "test_files", file_name
        )
        with open(testfile, "rb") as datafile:
            data_file = base64.b64encode(datafile.read())
            import_wizard = self.env["account.bank.statement.import"].create(
                {"attachment_ids": [(0, 0, {"name": file_name, "datas": data_file})]}
            )
            import_wizard.with_context(
                {
                    "account_bank_statement_import_adyen": True,
                    "journal_id": self.journal.id,
                }
            ).import_file()
            # statement name is account number + '-' + date of last line.
            statements = self.env["account.bank.statement"].search(
                [("name", "=", statement_name)]
            )
            self.assertTrue(statements)
            return statements
