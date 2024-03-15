# Copyright 2013-2016 Therp BV <https://therp.nl>
# Copyright 2017 Open Net Sàrl
# Copyright 2020 Camptocamp
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import difflib
import pprint
import tempfile
from datetime import date
from pathlib import Path

from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestParserCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.parser = cls.env["account.statement.import.camt.parser"]

    def _do_parse_test(self, inputfile, goldenfile, max_diff_count=None):
        """Imports ``inputfile`` and confronts its output against ``goldenfile`` data

        An AssertionError is raised if max_diff_count < 0

        :param inputfile: file to import and test
        :type inputfile: Path or str
        :param goldenfile: file to use for comparison (the expected values)
        :type goldenfile: Path or str
        :param max_diff_count: maximum nr of lines that can differ (default: 2)
        :type max_diff_count: int
        """
        max_diff_count = max_diff_count or 2
        assert max_diff_count >= 0
        diff = self._get_files_diffs(*map(self._to_filepath, (inputfile, goldenfile)))
        self.assertLessEqual(
            len(diff),
            max_diff_count,
            f"Actual output doesn't match expected output:\n{''.join(diff)}",
        )

    def _get_files_diffs(self, inputfile_path, goldenfile_path) -> list:
        """Creates diffs between ``inputfile_path`` and ``goldenfile_path`` data

        :param inputfile_path: path for file to import and test
        :type inputfile_path: Path
        :param goldenfile_path: path for file to use for comparison (the expected values)
        :type goldenfile_path: Path
        """

        # Read the input file, store the actual imported values
        with open(get_module_resource(*inputfile_path.parts), "rb") as inputf:
            res = self.parser.parse(inputf.read())
        # Read the output file, store the expected imported values
        with open(get_module_resource(*goldenfile_path.parts), "r") as goldf:
            gold_name, gold_lines = goldf.name, goldf.readlines()
        # Save the imported values in a tmp file to compare them w/ the expected values
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".pydata") as tempf:
            pprint.pprint(res, tempf, width=160)
            tempf.seek(0)
            out_name, out_lines = tempf.name, tempf.readlines()
        # Return a list of diffs
        return list(difflib.unified_diff(gold_lines, out_lines, gold_name, out_name))

    def _to_filepath(self, file):
        """Converts ``obj`` to a ``pathlib.Path`` object

        For backward compatibility: allows ``obj`` to be just a string representing only
        a filename, and this method will convert it to filepath for files inside the
        ``test_files`` folder (this behavior was previously hardcoded in method
        ``TestParser._do_parse_test()``)

        :param obj: the object to convert
        :type obj: Path or str
        """
        if isinstance(file, str) and len(Path(file).parts) == 1:
            file = Path("account_statement_import_camt") / "test_files" / file
        return Path(file)


class TestParser(TestParserCommon):
    """Tests for the camt parser itself."""

    def test_parse(self):
        self._do_parse_test("test-camt053", "golden-camt053.pydata")

    def test_parse_camt054(self):
        self._do_parse_test("test-camt054", "golden-camt054.pydata")

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

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        eur = cls.env.ref("base.EUR")
        eur.write({"active": True})
        bank = cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL77ABNA0574908765",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998748",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["account.journal"].create(
            {
                "name": "Bank Journal - (test camt)",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": eur.id,
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
