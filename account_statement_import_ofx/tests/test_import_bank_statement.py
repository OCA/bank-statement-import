import base64
import datetime

from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestOfxFile(TransactionCase):
    """Tests for import bank statement ofx file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestOfxFile, self).setUp()
        self.asi_model = self.env["account.statement.import"]
        self.abs_model = self.env["account.bank.statement"]
        self.j_model = self.env["account.journal"]
        self.absl_model = self.env["account.bank.statement.line"]
        cur = self.env.ref("base.USD")
        # self.env.ref("base.main_company").currency_id = cur.id
        bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "123456",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        self.env["account.journal"].create(
            {
                "name": "Bank Journal TEST OFX",
                "code": "BNK12",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": cur.id,
            }
        )

        bank_iban_ofx = self.env["res.partner.bank"].create(
            {
                "acc_number": "FR7630001007941234567890185",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )

        self.env["account.journal"].create(
            {
                "name": "FR7630001007941234567890185",
                "code": "BNK13",
                "type": "bank",
                "bank_account_id": bank_iban_ofx.id,
                "currency_id": cur.id,
            }
        )

    def test_wrong_ofx_file_import(self):
        ofx_file_path = get_module_resource(
            "account_statement_import_ofx",
            "tests/test_ofx_file/",
            "test_ofx_wrong.ofx",
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
        ofx_file_path = get_module_resource(
            "account_statement_import_ofx", "tests/test_ofx_file/", "test_ofx.ofx"
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
        self.assertEqual(line.transaction_type, "pos")

    def test_ofx_file_import_field_mapping(self):
        ofx_file_path = get_module_resource(
            "account_statement_import_ofx",
            "tests/test_ofx_file/",
            "test_ofx_fields.ofx",
        )
        ofx_file = base64.b64encode(open(ofx_file_path, "rb").read())
        wizard = self.asi_model.create(
            {
                "statement_file": ofx_file,
                "statement_filename": "test_ofx_fields.ofx",
            }
        )
        wizard.import_file_button()
        statement = self.abs_model.search([("name", "like", "123456")])[0]
        self.assertAlmostEqual(statement.balance_start, 2156.56, places=2)
        self.assertAlmostEqual(statement.balance_end_real, 1632.11, places=2)

        def get_line(fitid):
            return self.absl_model.search(
                [
                    ("unique_import_id", "like", fitid),
                    ("statement_id", "=", statement.id),
                ]
            )

        # NAME, MEMO, CHECKNUM and TRNTYPE all present: each OFX field
        # lands in its own Odoo field
        full = get_line("319378")
        self.assertEqual(full.payment_ref, "Acme Landlord")
        self.assertEqual(full.narration, "<p>321 Rent payment August</p>")
        self.assertEqual(full.transaction_type, "check")
        self.assertEqual(full.ref, "321")

        # No NAME: payment_ref falls back to MEMO
        no_name = get_line("319379")
        self.assertEqual(no_name.payment_ref, "Electricity monthly")
        self.assertEqual(no_name.narration, "<p>Electricity monthly</p>")
        self.assertEqual(no_name.transaction_type, "directdebit")
        self.assertFalse(no_name.ref)

        # No NAME and no MEMO: payment_ref falls back to TRNTYPE
        bare = get_line("319380")
        self.assertEqual(bare.payment_ref, "int")
        self.assertFalse(bare.narration)
        self.assertEqual(bare.transaction_type, "int")
        self.assertFalse(bare.ref)

    def test_check_journal_bank_account(self):
        ofx_file_path = get_module_resource(
            "account_statement_import_ofx",
            "tests/test_ofx_file/",
            "test_ofx_iban.ofx",
        )
        ofx_file = base64.b64encode(open(ofx_file_path, "rb").read())
        bank_st = self.asi_model.create(
            {
                "statement_file": ofx_file,
                "statement_filename": "test_ofx_iban.ofx",
            }
        )
        bank_st.import_file_button()
