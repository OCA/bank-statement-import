# Copyright 2022 AGEPoly
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import base64
import difflib
import pprint
import tempfile
from datetime import date

from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase


class TestParser(TransactionCase):
    """Tests for the mrx parser itself."""

    def setUp(self):
        super(TestParser, self).setUp()
        self.parser = self.env["account.statement.import.mrx.parser"]

    def _do_parse_test(self, inputfile, goldenfile):
        testfile = get_module_resource(
            "account_statement_import_mrx", "test_files", inputfile
        )
        with open(testfile, "rb") as data:
            res = self.parser.parse(data.read())
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".pydata") as temp:
                pprint.pprint(res, temp, width=160)
                goldenfile_res = get_module_resource(
                    "account_statement_import_mrx", "test_files", goldenfile
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
        self._do_parse_test("MRX-v1-5-Sample-CH.xml", "MRX-v1-5-Sample-CH.pydata")

