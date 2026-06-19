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

    def _parse_ofx_memos(self, filename):
        """Return the list of transaction memos parsed from an OFX fixture.

        ``_check_ofx`` is fed the raw (decoded) file bytes, exactly as the
        base ``_parse_file`` does in production.
        """
        ofx_file_path = get_module_resource(
            "account_statement_import_ofx", "tests/test_ofx_file/", filename
        )
        with open(ofx_file_path, "rb") as fh:
            data_file = fh.read()
        ofx = self.asi_model._check_ofx(data_file=data_file)
        self.assertTrue(ofx, "%s should be recognized as a valid OFX file" % filename)
        return [
            transaction.memo
            for account in ofx.accounts
            for transaction in account.statement.transactions
        ]

    def test_ofx_encoding_latin(self):
        """UTF-8 body mislabeled as CHARSET:1252 (the reported bug).

        The accented "Á" produces byte 0x81, which is undefined in cp1252 and
        used to crash ofxparse with a UnicodeDecodeError.
        """
        memos = self._parse_ofx_memos("test_ofx_utf8_latin.ofx")
        self.assertIn("TRANSFERENCIA ROMÁRIO ção JOSÉ", memos)

    def test_ofx_encoding_cp1252(self):
        """Genuine cp1252 body with the Euro sign (0x80) and Western accents."""
        memos = self._parse_ofx_memos("test_ofx_cp1252_euro.ofx")
        self.assertIn("Loyer 850€ café Müller", memos)

    def test_ofx_encoding_utf8_euro(self):
        """UTF-8 body with characters outside latin-1 (€, em dash).

        These used to be silently corrupted into mojibake; they must be
        preserved verbatim.
        """
        memos = self._parse_ofx_memos("test_ofx_utf8_euro.ofx")
        self.assertIn("Paiement 850€ — café", memos)

    def test_ofx_encoding_asian(self):
        """UTF-8 body with CJK characters, far outside any 8-bit codepage."""
        memos = self._parse_ofx_memos("test_ofx_utf8_asian.ofx")
        self.assertIn("送金 日本 中文 결제", memos)
