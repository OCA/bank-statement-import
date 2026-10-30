# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, datetime
from unittest.mock import patch

from odoo.addons.base.tests.common import BaseCommon

TRANSACTIONS = [
    ("tx-a", datetime(2023, 3, 15, 9), 100.0),
    ("tx-b", datetime(2023, 3, 15, 15), 50.0),
    ("tx-c", datetime(2023, 3, 16, 10), -20.0),
    ("tx-d", datetime(2023, 3, 16, 11), 30.0),
]


def _obtain_statement_data(provider, date_since, date_until):
    """The provider: the transactions of the period"""
    return [
        {
            "unique_import_id": unique_import_id,
            "date": tx_date,
            "amount": amount,
            "payment_ref": unique_import_id,
        }
        for unique_import_id, tx_date, amount in TRANSACTIONS
        if date_since <= tx_date < date_until
    ], {}


class TestBalanceCheck(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "CHKB",
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.env["online.bank.statement.provider"].create(
            {"service": "dummy", "journal_id": cls.journal.id, "tz": "UTC"}
        )
        with cls._patch_provider():
            cls.provider._pull(datetime(2023, 3, 15), datetime(2023, 3, 17))
        cls.lines = cls.env["account.bank.statement.line"].search(
            [("journal_id", "=", cls.journal.id)], order="date, id"
        )

    @classmethod
    def _patch_provider(cls):
        # On the class of the registry, so that it wins over the other modules
        return patch.object(
            type(cls.env["online.bank.statement.provider"]),
            "_obtain_statement_data",
            _obtain_statement_data,
        )

    def _check(self):
        check = self.env["online.bank.statement.check"].create(
            {
                "provider_id": self.provider.id,
                "date_from": date(2023, 3, 15),
                "date_to": date(2023, 3, 16),
            }
        )
        with self._patch_provider():
            check.action_check()
        return check

    def test_check_matching(self):
        self.assertEqual(len(self.lines), 4)
        check = self._check()
        self.assertFalse(check.issue_ids)
        self.assertFalse(check.first_mismatch_date)
        self.assertEqual(check.day_ids.mapped("provider_amount"), [150.0, 10.0])
        self.assertEqual(check.day_ids.mapped("odoo_amount"), [150.0, 10.0])

    def test_check_issues(self):
        line_b = self.lines.filtered(lambda line: line.payment_ref == "tx-b")
        line_c = self.lines.filtered(lambda line: line.payment_ref == "tx-c")
        # Out of its statement, so that it can be deleted also in 19.0
        line_b.statement_id = False
        line_b.unlink()
        line_c.amount = -25.0
        manual = self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal.id,
                "date": date(2023, 3, 16),
                "amount": 5.0,
                "payment_ref": "manual",
            }
        )
        check = self._check()
        issues = {issue.issue_type: issue for issue in check.issue_ids}
        self.assertEqual(set(issues), {"missing", "amount", "extra"})
        self.assertEqual(issues["missing"].provider_amount, 50.0)
        self.assertEqual(issues["amount"].statement_line_id, line_c)
        self.assertEqual(issues["amount"].odoo_amount, -25.0)
        self.assertEqual(issues["extra"].statement_line_id, manual)
        self.assertEqual(check.first_mismatch_date, date(2023, 3, 15))
        self.assertEqual(check.day_ids.mapped("difference"), [-50.0, 0.0])
        self.assertEqual(check.day_ids.mapped("cumulative_difference"), [-50.0, -50.0])
        self.assertEqual(check.missing_count, 1)

        with self._patch_provider():
            check.action_import_missing()
        self.assertEqual(check.missing_count, 0)
        self.assertTrue(
            self.env["account.bank.statement.line"].search(
                [("journal_id", "=", self.journal.id), ("payment_ref", "=", "tx-b")]
            )
        )

    def test_check_date(self):
        line_d = self.lines.filtered(lambda line: line.payment_ref == "tx-d")
        line_d.date = date(2023, 3, 15)
        check = self._check()
        self.assertEqual(check.issue_ids.issue_type, "date")
        self.assertEqual(check.issue_ids.odoo_date, date(2023, 3, 15))
        self.assertEqual(check.issue_ids.provider_date, date(2023, 3, 16))
