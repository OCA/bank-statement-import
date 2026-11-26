import base64
import datetime
from unittest.mock import patch

import odoo.tests.common as common
from odoo.exceptions import UserError
from odoo.tools import file_open


class TestOfxFile(common.TransactionCase):
    """Tests for import bank statement ofx file format
    (account.statement.import)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.asi_model = cls.env["account.statement.import"]
        cls.abs_model = cls.env["account.bank.statement"]
        cls.absl_model = cls.env["account.bank.statement.line"]
        cur = cls.env.ref("base.USD")
        company = cls.env.ref("base.main_company")
        suspense_account = company.account_journal_suspense_account_id
        if not suspense_account:
            suspense_account = cls.env["account.account"].create(
                {
                    "name": "Suspense Account",
                    "code": "999999",
                    "account_type": "asset_current",
                }
            )
            company.account_journal_suspense_account_id = suspense_account
        bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "123456",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": company.id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["account.journal"].create(
            {
                "name": "Bank Journal TEST OFX",
                "code": "BNK12",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": cur.id,
            }
        )
        bank_iban_ofx = cls.env["res.partner.bank"].create(
            {
                "acc_number": "12345678901",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": company.id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["account.journal"].create(
            {
                "name": "Bank Journal TEST OFX IBAN",
                "code": "BNK13",
                "type": "bank",
                "bank_account_id": bank_iban_ofx.id,
                "currency_id": cur.id,
            }
        )

    def test_wrong_ofx_file_import(self):
        ofx_path = "account_statement_import_ofx/tests/test_ofx_file/test_ofx_wrong.ofx"
        with file_open(ofx_path, "rb") as ofx_file:
            ofx_bin_wrong = ofx_file.read()
            wizard = self.asi_model.create(
                {
                    "statement_file": base64.b64encode(ofx_bin_wrong),
                    "statement_filename": "test_ofx_wrong.ofx",
                }
            )
            self.assertFalse(wizard._check_ofx(data_file=ofx_bin_wrong))

    def test_ofx_file_import(self):
        ofx_path = "account_statement_import_ofx/tests/test_ofx_file/test_ofx.ofx"
        with file_open(ofx_path, "rb") as ofx_file:
            ofx_bin = ofx_file.read()
            wizard = self.asi_model.create(
                {
                    "statement_file": base64.b64encode(ofx_bin),
                    "statement_filename": "test_ofx.ofx",
                }
            )
            wizard.import_file_button()
            bank_st_record = self.abs_model.search([("name", "like", "123456")])[0]
            self.assertEqual(bank_st_record.balance_start, 2516.56)
            self.assertEqual(bank_st_record.balance_end_real, 2156.56)

            line = self.absl_model.search(
                [
                    ("payment_ref", "=", "Agrolait"),
                    ("statement_id", "=", bank_st_record.id),
                ]
            )[0]
            self.assertEqual(line.date, datetime.date(2013, 8, 24))

    def test_ofx_iban_file_import(self):
        ofx_path = "account_statement_import_ofx/tests/test_ofx_file/test_ofx_iban.ofx"
        with file_open(ofx_path, "rb") as ofx_file:
            ofx_bin = ofx_file.read()
            wizard = self.asi_model.create(
                {
                    "statement_file": base64.b64encode(ofx_bin),
                    "statement_filename": "test_ofx_iban.ofx",
                }
            )
            wizard.import_file_button()
            bank_st_record = self.abs_model.search([("name", "like", "12345678901")])[0]
            self.assertEqual(bank_st_record.balance_end_real, 2156.56)

    def test_ofx_transaction_checknum_and_memo(self):
        ofx_path = (
            "account_statement_import_ofx/tests/test_ofx_file/"
            "test_ofx_checknum_memo.ofx"
        )
        with file_open(ofx_path, "rb") as ofx_file:
            ofx_bin = ofx_file.read()
            wizard = self.asi_model.create(
                {
                    "statement_file": base64.b64encode(ofx_bin),
                    "statement_filename": "test_ofx_checknum_memo.ofx",
                }
            )
            wizard.import_file_button()
            line = self.absl_model.search([("payment_ref", "like", "Office Supplies")])[
                0
            ]
            self.assertIn("1001", line.payment_ref)
            self.assertIn("Paper and pens for Q3", line.payment_ref)

    def test_parse_file_error_handling(self):
        ofx_path = "account_statement_import_ofx/tests/test_ofx_file/test_ofx.ofx"
        with file_open(ofx_path, "rb") as ofx_file:
            ofx_bin = ofx_file.read()
            wizard = self.asi_model.create(
                {
                    "statement_file": base64.b64encode(ofx_bin),
                    "statement_filename": "test_ofx.ofx",
                }
            )
            ofx = wizard._check_ofx(ofx_bin)
            with patch.object(type(wizard), "_check_ofx", return_value=ofx):
                # Make account iteration fail by breaking the balance attribute
                for account in ofx.accounts:
                    account.statement.balance = "not_a_number"
                with self.assertRaises(UserError):
                    wizard._parse_file(ofx_bin)

    def test_parse_non_ofx_file(self):
        non_ofx_data = b"This is not an OFX file"
        wizard = self.asi_model.create(
            {
                "statement_file": base64.b64encode(non_ofx_data),
                "statement_filename": "test.txt",
            }
        )
        self.assertFalse(wizard._check_ofx(non_ofx_data))
