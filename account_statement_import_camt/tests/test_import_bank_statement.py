# Copyright 2013-2016 Therp BV <https://therp.nl>
# Copyright 2017 Open Net Sàrl
# Copyright 2020 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import difflib
import pprint
import tempfile
from datetime import date

from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestParser(TransactionCase):
    """Tests for the camt parser itself."""

    def setUp(self):
        super(TestParser, self).setUp()
        self.parser = self.env["account.statement.import.camt.parser"]

    def _do_parse_test(self, inputfile, goldenfile):
        testfile = get_module_resource(
            "account_statement_import_camt", "test_files", inputfile
        )
        with open(testfile, "rb") as data:
            res = self.parser.parse(data.read())
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".pydata") as temp:
                pprint.pprint(res, temp, width=160)
                goldenfile_res = get_module_resource(
                    "account_statement_import_camt", "test_files", goldenfile
                )
                with open(goldenfile_res, "r") as golden:
                    temp.seek(0)
                    diff = list(
                        difflib.unified_diff(
                            golden.readlines(), temp.readlines(), golden.name, temp.name
                        )
                    )
                    if len(diff) > 2:
                        self.fail(
                            "actual output doesn't match expected "
                            + "output:\n%s" % "".join(diff)
                        )

    def test_parse(self):
        self._do_parse_test("test-camt053", "golden-camt053.pydata")

    def test_parse_txdtls(self):
        self._do_parse_test("test-camt053-txdtls", "golden-camt053-txdtls.pydata")

    def test_parse_no_ntry(self):
        self._do_parse_test("test-camt053-no-ntry", "golden-camt053-no-ntry.pydata")


class TestImport(TransactionCase):
    """Run test to import camt import."""

    transactions = [
        {
            "account_number": "NL46ABNA0499998748",
            "amount": -754.25,
            "date": date(year=2014, month=1, day=5),
            "ref": "435005714488-ABNO33052620",
        },
        {
            "remote_account": "NL46ABNA0499998748",
            "transferred_amount": -564.05,
            "value_date": date(year=2014, month=1, day=5),
            "ref": "TESTBANK/NL/20141229/01206408",
        },
        {
            "remote_account": "NL46ABNA0499998748",
            "transferred_amount": -100.0,
            "value_date": date(year=2014, month=1, day=5),
            "ref": "TESTBANK/NL/20141229/01206407",
        },
        {
            "remote_account": "NL69ABNA0522123643",
            "transferred_amount": 1405.31,
            "value_date": date(year=2014, month=1, day=5),
            "ref": "115",
        },
    ]

    def setUp(self):
        super(TestImport, self).setUp()
        bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "NL77ABNA0574908765",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        self.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998748",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        self.env["account.journal"].create(
            {
                "name": "Bank Journal - (test camt)",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": self.env.ref("base.EUR").id,
            }
        )

    def test_statement_import(self):
        """Test correct creation of single statement."""
        testfile = get_module_resource(
            "account_statement_import_camt", "test_files", "test-camt053"
        )
        with open(testfile, "rb") as datafile:
            camt_file = base64.b64encode(datafile.read())

            self.env["account.statement.import"].create(
                {
                    "statement_filename": "test import",
                    "statement_file": camt_file,
                }
            ).import_file_button()

            bank_st_record = self.env["account.bank.statement"].search(
                [("name", "=", "1234Test/1")], limit=1
            )
            statement_lines = bank_st_record.line_ids
            self.assertTrue(
                any(
                    all(
                        line[key] == self.transactions[0][key]
                        for key in ["amount", "date", "ref"]
                    )
                    # TODO and bank_account_id was removed from line
                    # and line.bank_account_id.acc_number
                    # == self.transactions[0]["account_number"]
                    for line in statement_lines
                )
            )

    def test_zip_import(self):
        """Test import of multiple statements from zip file."""
        testfile = get_module_resource(
            "account_statement_import_camt", "test_files", "test-camt053.zip"
        )
        with open(testfile, "rb") as datafile:
            camt_file = base64.b64encode(datafile.read())
            self.env["account.statement.import"].create(
                {"statement_filename": "test import", "statement_file": camt_file}
            ).import_file_button()
            bank_st_record = self.env["account.bank.statement"].search(
                [("name", "in", ["1234Test/2", "1234Test/3"])]
            )

        self.assertTrue(all([st.line_ids for st in bank_st_record]))
        self.assertEqual(bank_st_record[0].line_ids.mapped("sequence"), [1, 2, 3])
