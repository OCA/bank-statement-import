# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path


class TestQifFile(TransactionCase):
    """Tests for import bank statement qif file format
    (account.bank.statement.import)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.statement_import_model = cls.env["account.statement.import"]
        cls.statement_line_model = cls.env["account.bank.statement.line"]
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test bank journal",
                "code": "TEST",
                "type": "bank",
                "currency_id": cls.env.company.currency_id.id,
            }
        )
        cls.partner = cls.env["res.partner"].create(
            {
                # Different case for trying insensitive case search
                "name": "EPIC Technologies",
            }
        )

    def test_qif_file_import(self):
        qif_file_path = file_path("account_statement_import_qif/tests/test_qif.qif")
        qif_file = base64.b64encode(open(qif_file_path, "rb").read())
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal.id
        ).create({"statement_file": qif_file, "statement_filename": "test_qif.qif"})
        wizard.import_file_button()
        statement = self.statement_line_model.search(
            [("payment_ref", "=", "YOUR LOCAL SUPERMARKET")],
            limit=1,
        ).statement_id
        self.assertAlmostEqual(statement.balance_end_real, -1896.09, 2)
        line = self.statement_line_model.search(
            [("payment_ref", "=", "Epic Technologies")],
            limit=1,
        )
        self.assertEqual(line.partner_id, self.partner)

    def test_check_qif(self):
        self.assertTrue(self.statement_import_model._check_qif(b"!Type:Bank\n"))
        self.assertFalse(self.statement_import_model._check_qif(b"DATE,AMOUNT\n"))

    def test_parse_file_not_supported(self):
        with self.assertRaises(UserError):
            self.statement_import_model._parse_file(b"DATE,AMOUNT\n")

    def test_parse_file_decipher_error(self):
        with self.assertRaises(UserError):
            self.statement_import_model._parse_file(b"!Type:\xff")

    def test_parse_file_invalid_header(self):
        with self.assertRaises(UserError):
            self.statement_import_model._parse_file(b"!Type:Invst\n")

    def test_parse_file_ccard(self):
        qif_data = b"!Type:CCard\nD01/31/2024\nT-10.50\nNCHK-001\nPCard Store\n^\n"
        currency_code, account_number, stmts_vals = (
            self.statement_import_model.with_context(
                journal_id=self.journal.id
            )._parse_file(qif_data)
        )
        self.assertEqual(currency_code, self.journal.currency_id.name)
        self.assertFalse(account_number)
        self.assertEqual(stmts_vals[0]["balance_end_real"], -10.5)
        self.assertEqual(len(stmts_vals[0]["transactions"]), 1)
        self.assertEqual(stmts_vals[0]["transactions"][0]["ref"], "CHK-001")
        self.assertEqual(stmts_vals[0]["transactions"][0]["payment_ref"], "Card Store")

    def test_complete_stmts_vals_partner_match_qif(self):
        qif_file_path = file_path("account_statement_import_qif/tests/test_qif.qif")
        qif_file = base64.b64encode(open(qif_file_path, "rb").read())
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal.id
        ).create({"statement_file": qif_file, "statement_filename": "test_qif.qif"})
        stmts_vals = [
            {
                "transactions": [
                    {
                        "payment_ref": "Epic Technologies",
                        "date": "2024-01-01",
                        "amount": -1.0,
                        "unique_import_id": "line-1",
                    }
                ]
            }
        ]
        res = wizard._complete_stmts_vals(stmts_vals, self.journal, None)
        self.assertEqual(res[0]["transactions"][0]["partner_id"], self.partner.id)

    def test_complete_stmts_vals_no_qif_keeps_partner_empty(self):
        non_qif_file = base64.b64encode(b"DATE,AMOUNT\n")
        wizard = self.statement_import_model.with_context(
            journal_id=self.journal.id
        ).create(
            {
                "statement_file": non_qif_file,
                "statement_filename": "test.csv",
            }
        )
        stmts_vals = [
            {
                "transactions": [
                    {
                        "payment_ref": "Epic Technologies",
                        "date": "2024-01-01",
                        "amount": -1.0,
                        "unique_import_id": "line-2",
                    }
                ]
            }
        ]
        res = wizard._complete_stmts_vals(stmts_vals, self.journal, None)
        self.assertFalse(res[0]["transactions"][0].get("partner_id"))
