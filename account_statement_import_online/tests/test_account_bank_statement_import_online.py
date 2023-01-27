# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# Copyright 2022-2023 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import logging
from datetime import date, datetime
from unittest import mock
from urllib.error import HTTPError

from dateutil.relativedelta import relativedelta
from odoo_test_helper import FakeModelLoader

from odoo import _, fields
from odoo.tests import common

_logger = logging.getLogger(__name__)

mock_obtain_statement_data = (
    "odoo.addons.account_statement_import_online.tests."
    + "online_bank_statement_provider_dummy.OnlineBankStatementProviderDummy."
    + "_obtain_statement_data"
)


class TestAccountBankAccountStatementImportOnline(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        # Load fake model
        cls.loader = FakeModelLoader(cls.env, cls.__module__)
        cls.loader.backup_registry()
        cls.addClassCleanup(cls.loader.restore_registry)
        from .online_bank_statement_provider_dummy import (
            OnlineBankStatementProviderDummy,
        )

        cls.loader.update_registry((OnlineBankStatementProviderDummy,))

        cls.now = fields.Datetime.now()
        cls.AccountAccount = cls.env["account.account"]
        cls.AccountJournal = cls.env["account.journal"]
        cls.OnlineBankStatementProvider = cls.env["online.bank.statement.provider"]
        cls.OnlineBankStatementPullWizard = cls.env["online.bank.statement.pull.wizard"]
        cls.AccountBankStatement = cls.env["account.bank.statement"]
        cls.AccountBankStatementLine = cls.env["account.bank.statement.line"]

        cls.journal = cls.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
            }
        )
        cls.provider = cls.OnlineBankStatementProvider.create(
            {
                "name": "Dummy Provider",
                "service": "dummy",
                "journal_id": cls.journal.id,
                "statement_creation_mode": "daily",
            }
        )

    def test_pull_mode_daily(self):
        self.provider.statement_creation_mode = "daily"
        self.provider.with_context(step={"hours": 2})._pull(
            self.now - relativedelta(days=1),
            self.now,
        )
        self._getExpectedStatements(2)

    def test_pull_mode_weekly(self):
        self.provider.statement_creation_mode = "weekly"
        self.provider.with_context(step={"hours": 8})._pull(
            self.now - relativedelta(weeks=1),
            self.now,
        )
        self._getExpectedStatements(2)

    def test_pull_mode_monthly(self):
        self.provider.statement_creation_mode = "monthly"
        self.provider.with_context(step={"hours": 8})._pull(
            self.now - relativedelta(months=1),
            self.now,
        )
        self._getExpectedStatements(2)

    def test_pull_scheduled(self):
        self.provider.next_run = self.now - relativedelta(days=15)
        self._getExpectedStatements(0)
        self.provider.with_context(step={"hours": 8})._scheduled_pull()
        self._getExpectedStatements(1)

    def test_pull_skip_duplicates_by_unique_import_id(self):
        self.provider.statement_creation_mode = "weekly"
        # Get for two weeks of data.
        self.provider.with_context(
            step={"hours": 8},
            override_date_since=self.now - relativedelta(weeks=2),
            override_date_until=self.now,
        )._pull(
            self.now - relativedelta(weeks=2),
            self.now,
        )
        expected_count = 14 * (24 / 8)
        self._getExpectedLines(expected_count)
        # Get two weeks, but one overlapping with previous.
        self.provider.with_context(
            step={"hours": 8},
            override_date_since=self.now - relativedelta(weeks=3),
            override_date_until=self.now - relativedelta(weeks=1),
        )._pull(
            self.now - relativedelta(weeks=3),
            self.now - relativedelta(weeks=1),
        )
        expected_count = 21 * (24 / 8)
        self._getExpectedLines(expected_count)
        # Get another day, but within statements already retrieved.
        self.provider.with_context(
            step={"hours": 8},
            override_date_since=self.now - relativedelta(weeks=1),
            override_date_until=self.now,
        )._pull(
            self.now - relativedelta(weeks=1),
            self.now,
        )
        self._getExpectedLines(expected_count)

    def test_interval_type_minutes(self):
        self.provider.interval_type = "minutes"
        self.provider._compute_update_schedule()

    def test_interval_type_hours(self):
        self.provider.interval_type = "hours"
        self.provider._compute_update_schedule()

    def test_interval_type_days(self):
        self.provider.interval_type = "days"
        self.provider._compute_update_schedule()

    def test_interval_type_weeks(self):
        self.provider.interval_type = "weeks"
        self.provider._compute_update_schedule()

    def test_pull_no_crash(self):
        self.provider.statement_creation_mode = "weekly"
        self.provider.with_context(crash=True, scheduled=True)._pull(
            self.now - relativedelta(hours=1),
            self.now,
        )
        self._getExpectedStatements(0)

    def test_pull_crash(self):
        self.provider.statement_creation_mode = "weekly"
        with self.assertRaisesRegex(Exception, "Expected"):
            self.provider.with_context(crash=True)._pull(
                self.now - relativedelta(hours=1),
                self.now,
            )

    def test_pull_httperror(self):
        self.provider.statement_creation_mode = "weekly"
        with self.assertRaises(HTTPError):
            self.provider.with_context(
                crash=True,
                exception=HTTPError(None, 500, "Error", None, None),
            )._pull(
                self.now - relativedelta(hours=1),
                self.now,
            )

    def test_pull_no_balance(self):
        self.provider.with_context(
            step={"hours": 2},
            balance_start=0,
            amount=100.0,
            balance=False,
        )._pull(
            self.now - relativedelta(days=1),
            self.now,
        )
        statements = self._getExpectedStatements(2)
        self.assertFalse(statements[0].balance_start)
        self.assertTrue(statements[0].balance_end)
        self.assertTrue(statements[1].balance_start)

    def test_wizard(self):
        vals = {
            "date_since": self.now - relativedelta(hours=1),
            "date_until": self.now,
        }
        wizard = self.OnlineBankStatementPullWizard.with_context(
            active_model=self.provider._name, active_id=self.provider.id
        ).create(vals)
        wizard.action_pull()
        self._getExpectedStatements(1)

    def test_wizard_on_journal(self):
        vals = {
            "date_since": self.now - relativedelta(hours=1),
            "date_until": self.now,
        }
        wizard = self.OnlineBankStatementPullWizard.with_context(
            active_model=self.journal._name, active_id=self.journal.id
        ).create(vals)
        wizard.action_pull()
        self._getExpectedStatements(1)

    def test_pull_statement_partially(self):
        self.provider.statement_creation_mode = "monthly"
        provider_context = {
            "step": {"hours": 24},
            "override_date_since": datetime(2020, 1, 1),
            "amount": 1.0,
            "balance_start": 0,
        }
        # Should create statement for first 30 days of january.
        self.provider.with_context(
            **provider_context,
            override_date_until=datetime(2020, 1, 31),
        )._pull(
            datetime(2020, 1, 1),
            datetime(2020, 1, 31),
        )
        statements = self._getExpectedStatements(1)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 30.0)
        # Should create statement for first 14 days of february,
        # and add one line to statement for january.
        self.provider.with_context(
            **provider_context,
            override_date_until=datetime(2020, 2, 15),
        )._pull(
            datetime(2020, 1, 1),
            datetime(2020, 2, 29),
        )
        statements = self._getExpectedStatements(2)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 31.0)
        self.assertEqual(statements[1].balance_start, 31.0)
        self.assertEqual(statements[1].balance_end_real, 45.0)
        # Getting data for rest of februari should not create new statement.
        self.provider.with_context(
            **provider_context,
            override_date_until=datetime(2020, 2, 29),
        )._pull(
            datetime(2020, 1, 1),
            datetime(2020, 2, 29),
        )
        statements = self._getExpectedStatements(2)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 31.0)
        self.assertEqual(statements[1].balance_start, 31.0)
        self.assertEqual(statements[1].balance_end_real, 59.0)

    def test_tz_utc(self):
        self.provider.tz = "UTC"
        self.provider.with_context(
            step={"hours": 1},
            override_date_since=datetime(2020, 4, 17, 22, 0),
            override_date_until=datetime(2020, 4, 18, 2, 0),
            tz="UTC",
        )._pull(
            datetime(2020, 4, 17, 22, 0),
            datetime(2020, 4, 18, 2, 0),
        )
        statements = self._getExpectedStatements(2)
        lines = statements.mapped("line_ids").sorted(key=lambda r: r.id)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 17))
        self.assertEqual(lines[1].date, date(2020, 4, 17))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def test_tz_non_utc(self):
        """Test situation where the provider is west of Greenwich.

        In this case, when it is 22:00 according to the provider, it is
        00:00 the next day according to GMT/UTZ.
        """
        self.provider.tz = "Etc/GMT-2"
        self.provider.with_context(
            step={"hours": 1},
            override_date_since=datetime(2020, 4, 17, 22, 0),
            override_date_until=datetime(2020, 4, 18, 2, 0),
            tz="UTC",
        )._pull(
            datetime(2020, 4, 17, 22, 0),
            datetime(2020, 4, 18, 2, 0),
        )
        statements = self._getExpectedStatements(2)
        lines = statements.mapped("line_ids").sorted(key=lambda r: r.id)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 18))
        self.assertEqual(lines[1].date, date(2020, 4, 18))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def test_other_tz_to_utc(self):
        """Test the situation where we are tot the west of the provider.

        Provider will be GMT/UTC, we will be two hours to the west.
        When we pull data from 22:00 on the 17th of april, for
        the provider this will be from 00:00 on the 18th.

        We will translate the provider times back to our time.
        """
        self.provider.with_context(
            step={"hours": 1},
            tz="Etc/GMT-2",
            override_date_since=datetime(2020, 4, 18, 0, 0),
            override_date_until=datetime(2020, 4, 18, 4, 0),
        )._pull(
            datetime(2020, 4, 17, 22, 0),
            datetime(2020, 4, 18, 2, 0),
        )
        statements = self._getExpectedStatements(2)
        lines = statements.mapped("line_ids").sorted(key=lambda r: r.id)
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 17))
        self.assertEqual(lines[1].date, date(2020, 4, 17))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def test_timestamp_date_only_date(self):
        self.provider.with_context(step={"hours": 1}, timestamp_mode="date")._pull(
            datetime(2020, 4, 18, 0, 0),
            datetime(2020, 4, 18, 4, 0),
        )
        statements = self._getExpectedStatements(1)
        lines = statements.line_ids
        self.assertEqual(len(lines), 24)
        for line in lines:
            self.assertEqual(line.date, date(2020, 4, 18))

    def test_timestamp_date_only_str(self):
        self.provider.with_context(
            step={"hours": 1},
            override_date_since=datetime(2020, 4, 18, 0, 0),
            override_date_until=datetime(2020, 4, 18, 4, 0),
            timestamp_mode="str",
        )._pull(
            datetime(2020, 4, 18, 0, 0),
            datetime(2020, 4, 18, 4, 0),
        )
        statements = self._getExpectedStatements(1)
        lines = statements.line_ids
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 18))
        self.assertEqual(lines[1].date, date(2020, 4, 18))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def _get_statement_line_data(self, statement_date):
        return [
            {
                "payment_ref": "payment",
                "amount": 100,
                "date": statement_date,
                "unique_import_id": str(statement_date),
                "partner_name": "John Doe",
                "account_number": "XX00 0000 0000 0000",
            }
        ], {}

    def test_dont_create_empty_statements(self):
        """Test the default behavior of not creating empty bank
        statements ('Allow empty statements' field is uncheck at the
        provider level.).
        """
        with mock.patch(mock_obtain_statement_data) as mock_data:
            mock_data.side_effect = [
                self._get_statement_line_data(date(2021, 8, 10)),
                ([], {}),  # August 8th, doesn't have statement
                ([], {}),  # August 9th, doesn't have statement
                self._get_statement_line_data(date(2021, 8, 13)),
            ]
            self.provider._pull(datetime(2021, 8, 10), datetime(2021, 8, 14))
        statements = self._getExpectedStatements(2)
        self.assertEqual(statements[0].balance_start, 0)
        self.assertEqual(statements[0].balance_end, 100)
        self.assertEqual(len(statements[0].line_ids), 1)
        self.assertEqual(statements[1].balance_start, 100)
        self.assertEqual(statements[1].balance_end, 200)
        self.assertEqual(len(statements[1].line_ids), 1)

    def test_unlink_provider(self):
        """Unlink provider should clear fields on journal."""
        self.provider.unlink()
        self.assertEqual(self.journal.bank_statements_source, "undefined")
        self.assertEqual(self.journal.online_bank_statement_provider, False)
        self.assertEqual(self.journal.online_bank_statement_provider_id.id, False)

    def _getExpectedStatements(self, expected_length):
        """Check for length of statement recordset, with helpfull logging."""
        statements = self.AccountBankStatement.search(
            [("journal_id", "=", self.journal.id)], order="date asc"
        )
        actual_length = len(statements)
        # If length not expected, log information about statements.
        if actual_length != expected_length:
            if actual_length == 0:
                _logger.warning(
                    _("No statements found in journal"),
                )
            else:
                _logger.warning(
                    _("Names and dates for statements found: %(statements)s"),
                    dict(
                        statements=", ".join(
                            ["%s - %s" % (stmt.name, stmt.date) for stmt in statements]
                        )
                    ),
                )
        # Now do the normal assert.
        self.assertEqual(len(statements), expected_length)
        # If we got expected number, return them.
        return statements

    def _getExpectedLines(self, expected_length):
        """Check number of lines created."""
        lines = self.AccountBankStatementLine.search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(len(lines), expected_length)
        # If we got expected number, return them.
        return lines
