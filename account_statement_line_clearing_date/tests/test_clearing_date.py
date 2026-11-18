# Copyright 2026 ForgeFlow S.L. (https://www.forgeflow.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import Command, fields
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestClearingDate(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.bsl_model = cls.env["account.bank.statement.line"]
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Clearing",
                "type": "bank",
                "code": "TCLR",
                "company_id": cls.env.company.id,
            }
        )

    def _line(self, amount, date, clearing_date=False):
        return self.bsl_model.create(
            {
                "journal_id": self.journal.id,
                "date": date,
                "payment_ref": f"{amount}@{date}",
                "amount": amount,
                "clearing_date": clearing_date,
            }
        )

    def _statement(self, lines, **vals):
        vals["line_ids"] = [Command.set(lines.ids)]
        stmt = self.env["account.bank.statement"].create(vals)
        stmt._compute_balance_start()
        return stmt

    def _build_clearing_scenario(self):
        # Three month statements. March stmt contains delayed line purchased
        # Jan 5 but cleared Mar 15. Returns statements and delayed line:
        #   Jan: start 0   -> end 150
        line_jan_1 = self._line(100, "2020-01-10")
        line_jan_2 = self._line(50, "2020-01-20")
        jan = self._statement(line_jan_1 | line_jan_2)
        #   Feb: start 150 -> end 170
        line_feb_1 = self._line(30, "2020-02-10")
        line_feb_2 = self._line(-10, "2020-02-20")
        feb = self._statement(line_feb_1 | line_feb_2)
        #   Mar: start 170 -> end 203 (20 + 8 delayed + 5)
        line_mar_1 = self._line(20, "2020-03-10")
        line_mar_2 = self._line(5, "2020-03-20")
        delayed = self._line(8, "2020-01-05", clearing_date="2020-03-15")
        mar = self._statement(line_mar_1 | delayed | line_mar_2)
        return jan, feb, mar, delayed

    def test_clearing_date_drives_index_without_touching_date(self):
        line1 = self._line(100.0, "2026-03-03", clearing_date="2026-05-29")
        # Chronological index follows the clearing date
        # The accounting date is left untouched
        self.assertTrue(line1.internal_index.startswith("20260529"))
        self.assertEqual(line1.date, fields.Date.to_date("2026-03-03"))
        # No clearing date falls back to accounting date
        line2 = self._line(100.0, "2026-03-03")
        self.assertTrue(line2.internal_index.startswith("20260303"))

    def test_statement_earliest_settled_line_without_clearing(self):
        # A delayed line (purchased Mar 1, cleared May 31) grouped with a
        # normal late-April line in the same statement
        delayed = self._line(-100.0, "2026-03-03", clearing_date="2026-05-29")
        normal = self._line(-50.0, "2026-04-26")
        statement = self._statement(delayed | normal)
        # Statement not dragged back to March, and uses normal as first line
        self.assertTrue(statement.first_line_index.startswith("20260426"))
        self.assertEqual(statement.first_line_index, normal.internal_index)
        self.assertEqual(statement.date, fields.Date.to_date("2026-05-29"))

    def test_statement_earliest_settled_line_with_clearing(self):
        # A delayed line (purchased Mar 1, cleared Apr 20) grouped with a
        # normal late-April line in the same statement
        delayed = self._line(-100.0, "2026-03-03", clearing_date="2026-04-20")
        normal = self._line(-50.0, "2026-04-26")
        statement = self._statement(delayed | normal)
        # Statement not dragged back to March, and uses delayed as first line
        self.assertTrue(statement.first_line_index.startswith("20260420"))
        self.assertEqual(statement.first_line_index, delayed.internal_index)
        self.assertEqual(statement.date, fields.Date.to_date("2026-04-26"))

    def test_multi_statement_all_valid_with_clearing(self):
        jan, feb, mar, _delayed = self._build_clearing_scenario()
        stmts = jan | feb | mar
        # Chronological order by first_line_index
        self.assertEqual(
            stmts.sorted("first_line_index"),
            jan + feb + mar,
        )
        stmts.invalidate_recordset(["is_valid"])
        self.assertTrue(all(stmts.mapped("is_valid")))

    def test_balance_start_chain_with_clearing(self):
        jan, feb, mar, _delayed = self._build_clearing_scenario()
        self.assertRecordValues(
            jan + feb + mar,
            [
                {"balance_start": 0.0, "balance_end_real": 150.0},
                {"balance_start": 150.0, "balance_end_real": 170.0},
                {"balance_start": 170.0, "balance_end_real": 203.0},
            ],
        )
        # Delayed line's amount lands in March's balance, not January
        self.assertRecordValues(mar, [{"balance_end": 203.0, "is_complete": True}])

    def test_running_balance_with_clearing(self):
        self._build_clearing_scenario()
        self.bsl_model.invalidate_model(["running_balance"])
        # Lines ordered by internal_index DESC (newest first)
        lines = self.bsl_model.search([("journal_id", "=", self.journal.id)])
        self.assertRecordValues(
            lines,
            [
                {"amount": 5.0, "running_balance": 203.0},  # Mar 20
                {"amount": 8.0, "running_balance": 198.0},  # cleared Mar 15
                {"amount": 20.0, "running_balance": 190.0},  # Mar 10 (170 + 20)
                {"amount": -10.0, "running_balance": 170.0},  # Feb 20
                {"amount": 30.0, "running_balance": 180.0},  # Feb 10 (150 + 30)
                {"amount": 50.0, "running_balance": 150.0},  # Jan 20
                {"amount": 100.0, "running_balance": 100.0},  # Jan 10 (0 + 100)
            ],
        )

    def test_bug_then_fix_validity(self):
        line_1_jan = self._line(100, "2020-01-10")
        line_2_jan = self._line(50, "2020-01-20")
        jan = self._statement(line_1_jan | line_2_jan)
        line_1_feb = self._line(30, "2020-02-10")
        line_2_feb = self._line(-10, "2020-02-20")
        feb = self._statement(line_1_feb | line_2_feb)
        line_1_mar = self._line(20, "2020-03-10")
        line_2_mar = self._line(5, "2020-03-20")
        mar = self._statement(line_1_mar | line_2_mar)
        stmts = jan | feb | mar
        stmts.invalidate_recordset(["is_valid"])
        self.assertTrue(all(stmts.mapped("is_valid")), "clean chain starts valid")
        # Import a delayed transaction (purchased Jan 5) into March, no clearing
        # date -> March is dragged before January and the chain breaks
        delayed = self._line(8, "2020-01-05")
        delayed.statement_id = mar
        mar.flush_recordset(["first_line_index"])
        self.assertTrue(mar.first_line_index.startswith("20200105"))
        stmts.invalidate_recordset(["is_valid"])
        self.assertFalse(jan.is_valid)
        # Set the clearing date -> March snaps back after February, chain heals
        # and no transaction date mutated
        delayed.clearing_date = "2020-03-15"
        mar.flush_recordset(["first_line_index"])
        self.assertTrue(mar.first_line_index.startswith("20200310"))
        stmts.invalidate_recordset(["is_valid"])
        self.assertTrue(all(stmts.mapped("is_valid")))
