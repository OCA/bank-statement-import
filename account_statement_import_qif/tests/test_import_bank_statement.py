# Copyright 2015 Odoo S. A.
# Copyright 2015 Laurent Mignon <laurent.mignon@acsone.eu>
# Copyright 2015 Ronald Portier <rportier@therp.nl>
# Copyright 2016-2017 Tecnativa - Pedro M. Baeza
# Copyright 2024 Tecnativa - Víctor Martínez
# Copyright 2026 Ryan Duguid <ryan@duguid.com.au>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
from datetime import date

from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path

from odoo.addons.account_statement_import_qif.qif_dates import qif_file_dayfirst


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

    def _parse_qif(self, data, journal=None):
        journal = journal or self.journal
        wizard = self.statement_import_model.with_context(journal_id=journal.id).create(
            {
                "statement_file": base64.b64encode(data),
                "statement_filename": "test.qif",
            }
        )
        return wizard._parse_file(data)

    def test_qif_file_import(self):
        qif_file_path = file_path("account_statement_import_qif/tests/test_qif.qif")
        with open(qif_file_path, "rb") as qif_stream:
            qif_file = base64.b64encode(qif_stream.read())
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
        self.assertEqual(line.date, date(2013, 3, 3))

    def test_qif_file_dayfirst_detection(self):
        self.assertTrue(qif_file_dayfirst(["31/07/2026", "08/07/2026", "01/07/2026"]))
        self.assertFalse(qif_file_dayfirst(["8/12/13", "8/15/13", "3/3/13"]))
        self.assertIsNone(qif_file_dayfirst(["08/07/2026", "01/07/2026"]))
        self.assertIsNone(qif_file_dayfirst(["2026-07-31"]))

    def test_qif_australian_dates_from_file(self):
        """A day > 12 in the file proves dd/mm for the whole statement.

        Without a file-level hint, dateutil parses 08/07/2026 as 7 August
        and 01/07/2026 as 7 January, which is the #982 Australian QIF bug.
        """
        qif_file_path = file_path("account_statement_import_qif/tests/test_qif_au.qif")
        with open(qif_file_path, "rb") as qif_file:
            _currency, _account, stmts = self._parse_qif(qif_file.read())
        dates = [line["date"] for line in stmts[0]["transactions"]]
        self.assertEqual(
            dates,
            [date(2026, 7, 31), date(2026, 7, 8), date(2026, 7, 1)],
        )

    def test_qif_australian_ambiguous_dates_use_company_country(self):
        self.env.company.country_id = self.env.ref("base.au")
        data = (
            b"!Type:Bank\n"
            b"D08/07/2026\nT360.00\nPTransaction 2\n^\n"
            b"D01/07/2026\nT0.00\nPTransaction 3\n^\n"
        )
        _currency, _account, stmts = self._parse_qif(data)
        dates = [line["date"] for line in stmts[0]["transactions"]]
        self.assertEqual(dates, [date(2026, 7, 8), date(2026, 7, 1)])

    def test_qif_us_ambiguous_dates_stay_month_first(self):
        self.env.company.country_id = self.env.ref("base.us")
        data = (
            b"!Type:Bank\n"
            b"D08/07/2026\nT360.00\nPTransaction 2\n^\n"
            b"D01/07/2026\nT0.00\nPTransaction 3\n^\n"
        )
        _currency, _account, stmts = self._parse_qif(data)
        dates = [line["date"] for line in stmts[0]["transactions"]]
        self.assertEqual(dates, [date(2026, 8, 7), date(2026, 1, 7)])

    def test_qif_iso_dates_keep_year_month_day_order(self):
        self.env.company.country_id = self.env.ref("base.au")
        for prefix in (b"", b"D31/07/2026\nT10.00\nPDay-first transaction\n^\n"):
            with self.subTest(prefix=prefix):
                data = (
                    b"!Type:Bank\n"
                    + prefix
                    + b"D2026-07-08\nT360.00\nPISO transaction\n^\n"
                )
                _currency, _account, stmts = self._parse_qif(data)
                self.assertEqual(stmts[0]["transactions"][-1]["date"], date(2026, 7, 8))
