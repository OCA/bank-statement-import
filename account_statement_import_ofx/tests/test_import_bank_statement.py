import base64
import datetime

import odoo.tests.common as common
from odoo.tools.misc import file_path


class TestOfxFile(common.TransactionCase):
    """Tests for import bank statement ofx file format
    (account.bank.statement.import)
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.asi_model = cls.env["account.statement.import"]
        cls.abs_model = cls.env["account.bank.statement"]
        cls.absl_model = cls.env["account.bank.statement.line"]
        cur = cls.env.ref("base.USD")
        bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "123456",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
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
                "acc_number": "FR7630001007941234567890185",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["account.journal"].create(
            {
                "name": "FR7630001007941234567890185",
                "code": "BNK13",
                "type": "bank",
                "bank_account_id": bank_iban_ofx.id,
                "currency_id": cur.id,
            }
        )

    def test_wrong_ofx_file_import(self):
        ofx_file_path = file_path(
            "account_statement_import_ofx/tests/test_ofx_file/test_ofx_wrong.ofx"
        )
        ofx_file_wrong = base64.b64encode(open(ofx_file_path, "rb").read())
        bank_statement = self.asi_model.create(
            {
                "statement_file": ofx_file_wrong,
                "statement_filename": "test_ofx_wrong.ofx",
            }
        )
        self.assertFalse(bank_statement._check_ofx(data_file=ofx_file_wrong))

    def test_ofx_file_import(self):
        ofx_file_path = file_path(
            "account_statement_import_ofx/tests/test_ofx_file/test_ofx.ofx"
        )
        ofx_file = base64.b64encode(open(ofx_file_path, "rb").read())
        bank_statement = self.asi_model.create(
            {
                "statement_file": ofx_file,
                "statement_filename": "test_ofx.ofx",
            }
        )
        bank_statement.import_file_button()
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

    def test_check_journal_bank_account(self):
        ofx_file_path = file_path(
            "account_statement_import_ofx/tests/test_ofx_file/test_ofx_iban.ofx"
        )
        ofx_file = base64.b64encode(open(ofx_file_path, "rb").read())
        bank_st = self.asi_model.create(
            {
                "statement_file": ofx_file,
                "statement_filename": "test_ofx_iban.ofx",
            }
        )
        bank_st.import_file_button()
