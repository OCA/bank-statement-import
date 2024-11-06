# Copyright 2024 Sygel - Manuel Regidor
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html

import base64

import odoo.tests.common as common
from odoo.exceptions import UserError
from odoo.tools.misc import file_path


class TestAccountStatementImportFile(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.eur_currency.write({"active": True})
        cls.bank_account = cls.env["res.partner.bank"].create(
            {"acc_number": "1111111111", "partner_id": cls.env.company.partner_id.id}
        )
        cls.bank_account_2 = cls.env["res.partner.bank"].create(
            {"acc_number": "3333333333", "partner_id": cls.env.company.partner_id.id}
        )
        cls.journal_1 = cls.env["account.journal"].create(
            {
                "name": "Test asset journal-1",
                "code": "AST-1",
                "type": "bank",
                "bank_account_id": cls.bank_account.id,
            }
        )
        cls.journal_2 = cls.env["account.journal"].create(
            {
                "name": "Test asset journal-2",
                "code": "AST-2",
                "type": "bank",
                "bank_account_id": cls.bank_account.id,
            }
        )
        f_path = file_path(
            "account_statement_import_file/tests/samples/test_statement_import.txt"
        )
        file = base64.b64encode(open(f_path, "rb").read())
        cls.import_wizard = (
            cls.env["account.statement.import"]
            .with_context(journal_id=cls.journal_1.id)
            .create({"statement_file": file, "statement_filename": "Test"})
        )

    def test_complete_stmts_vals(self):
        # ERROR: Missing payment_ref on a transaction.
        import_wizard = self.import_wizard
        stmts_vals = [{"transactions": [{"payment_ref": ""}]}]
        with self.assertRaises(UserError):
            import_wizard._complete_stmts_vals(stmts_vals, self.journal_1, "1111111111")

    def test_match_journal(self):
        import_wizard = self.import_wizard

        # ERROR: The format of this bank statement file doesn't "
        # contain the bank account number, so you must
        # start the wizard from the right bank journal
        # in the dashboard.
        with self.assertRaises(UserError):
            import_wizard.with_context(journal_id=False)._match_journal(
                False, self.eur_currency
            )

        # ERROR: The journal found for the file (%(journal_match)s) is "
        # "different from the selected journal (%(journal_selected)s).
        with self.assertRaises(UserError):
            import_wizard.with_context(journal_id=self.journal_2.id)._match_journal(
                "1111111111", self.eur_currency
            )

        # ERROR: The bank account with number '%(account_number)s' exists in Odoo
        # but it is not set on any bank journal. You should
        # set it on the related bank journal. If the related
        # bank journal doesn't exist yet, you should create
        # a new one.
        self.journal_1.write({"type": "general"})
        self.journal_2.write({"type": "general"})
        with self.assertRaises(UserError):
            import_wizard.with_context(journal_id=self.journal_2.id)._match_journal(
                "1111111111", self.eur_currency
            )

        # ERROR: Could not find any bank account with number '%(account_number)s'
        # linked to partner '%(partner_name)s'. You should create the bank
        # account and set it on the related bank journal.
        # If the related bank journal doesn't exist yet, you
        # should create a new one."
        with self.assertRaises(UserError):
            import_wizard.with_context(journal_id=self.journal_2.id)._match_journal(
                "2222222222", self.eur_currency
            )

    def test_import_single_statement(self):
        import_wizard = self.import_wizard
        # ERROR: The parsing of the statement file returned an invalid result.
        vals = [1, 1, {"val1: 1"}]
        result = {"statement_ids": [], "notifications": []}
        with self.assertRaises(UserError):
            import_wizard.import_single_statement(vals, result)

        # ERROR: Missing currency code in the bank statement file.
        vals = (
            False,
            "2910907154",
            [
                {
                    "transactions": [
                        {
                            "payment_ref": "PAYMENT REF",
                            "ref": "REF",
                            "amount": -1,
                            "partner_name": "PARTNER",
                        },
                    ],
                    "balance_start": 10,
                    "balance_end_real": 9,
                }
            ],
        )
        with self.assertRaises(UserError):
            import_wizard.import_single_statement(vals, result)

        # ERROR: The bank statement file uses currency '%s' but there is no
        # such currency in Odoo."
        vals = (
            "NOK",
            "2910907154",
            [
                {
                    "transactions": [
                        {
                            "payment_ref": "PAYMENT REF",
                            "ref": "REF",
                            "amount": -1,
                            "partner_name": "PARTNER",
                        },
                    ],
                    "balance_start": 10,
                    "balance_end_real": 9,
                }
            ],
        )
        with self.assertRaises(UserError):
            import_wizard.import_single_statement(vals, result)
