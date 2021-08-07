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
        self.absi_model = self.env["account.bank.statement.import"]
        self.abs_model = self.env["account.bank.statement"]
        self.j_model = self.env["account.journal"]
        self.absl_model = self.env["account.bank.statement.line"]
        self.ia_model = self.env["ir.attachment"]
        cur = self.env.ref("base.USD")
        self.env.ref("base.main_company").currency_id = cur.id
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
            }
        )

    def test_wrong_ofx_file_import(self):
        ofx_file_path = get_module_resource(
            "account_bank_statement_import_ofx",
            "tests/test_ofx_file/",
            "test_ofx_wrong.ofx",
        )
        ofx_file_wrong = base64.b64encode(open(ofx_file_path, "rb").read())
        attach = self.ia_model.create(
            {"name": "test_ofx_wrong.ofx", "datas": ofx_file_wrong}
        )
        bank_statement = self.absi_model.create(
            dict(attachment_ids=[(6, 0, [attach.id])])
        )
        self.assertFalse(bank_statement._check_ofx(data_file=ofx_file_wrong))

    def test_ofx_file_import(self):
        ofx_file_path = get_module_resource(
            "account_bank_statement_import_ofx", "tests/test_ofx_file/", "test_ofx.ofx"
        )
        ofx_file = base64.b64encode(open(ofx_file_path, "rb").read())
        attach = self.ia_model.create({"name": "test_ofx.ofx", "datas": ofx_file})
        bank_statement = self.absi_model.create(
            dict(attachment_ids=[(6, 0, [attach.id])])
        )
        bank_statement.import_file()
        bank_st_record = self.abs_model.search([("name", "like", "123456")])[0]
        self.assertEqual(bank_st_record.balance_start, 2516.56)
        self.assertEqual(bank_st_record.balance_end_real, 2156.56)

        line = self.absl_model.search(
            [("name", "=", "Agrolait"), ("statement_id", "=", bank_st_record.id)]
        )[0]
        self.assertEqual(line.ref, "219378")
        self.assertEqual(line.date, datetime.date(2013, 8, 24))

    def test_check_journal_bank_account(self):
        ofx_file_path = get_module_resource(
            "account_bank_statement_import_ofx",
            "tests/test_ofx_file/",
            "test_ofx_iban.ofx",
        )
        ofx_file = base64.b64encode(open(ofx_file_path, "rb").read())
        attach = self.ia_model.create({"name": "test_ofx.ofx", "datas": ofx_file})
        bank_st = self.absi_model.create(dict(attachment_ids=[(6, 0, [attach.id])]))
        journal_iban_ofx = self.j_model.search(
            [("name", "=", "FR7630001007941234567890185")]
        )
        res = bank_st._check_journal_bank_account(journal_iban_ofx, "12345678901")
        self.assertTrue(res)
        bank_st.with_context(journal_id=journal_iban_ofx.id).import_file()
