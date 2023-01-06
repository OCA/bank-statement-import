# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, datetime
from unittest import mock
from urllib.error import HTTPError

from dateutil.relativedelta import relativedelta
from odoo_test_helper import FakeModelLoader
from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import common
from odoo.tools import mute_logger

mock_obtain_statement_data = (
    "odoo.addons.account_statement_import_online.tests."
    + "online_bank_statement_provider_dummy.OnlineBankStatementProviderDummy."
    + "_obtain_statement_data"
)


class TestAccountAccountStatementImportOnline(common.SavepointCase):
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
        cls.AccountJournal = cls.env["account.journal"]
        cls.OnlineBankStatementProvider = cls.env["online.bank.statement.provider"]
        cls.OnlineBankStatementPullWizard = cls.env["online.bank.statement.pull.wizard"]
        cls.AccountBankStatement = cls.env["account.bank.statement"]
        cls.AccountBankStatementLine = cls.env["account.bank.statement.line"]

    def test_provider_unlink_restricted(self):
        journal = self.AccountJournal.create(
            {"name": "Bank", "type": "bank", "code": "BANK"}
        )
        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = "online"
            journal_form.online_bank_statement_provider = "dummy"
        journal_form.save()

        with self.assertRaises(IntegrityError), mute_logger("odoo.sql_db"):
            journal.online_bank_statement_provider_id.unlink()

    def test_cascade_unlink(self):
        journal = self.AccountJournal.create(
            {"name": "Bank", "type": "bank", "code": "BANK"}
        )
        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = "online"
            journal_form.online_bank_statement_provider = "dummy"
        journal_form.save()

        self.assertTrue(journal.online_bank_statement_provider_id)
        save_provider_id = journal.online_bank_statement_provider_id.id
        journal.unlink()
        self.assertFalse(
            self.OnlineBankStatementProvider.search(
                [
                    ("id", "=", save_provider_id),
                ]
            )
        )

    def test_source_change_cleanup(self):
        journal = self.AccountJournal.create(
            {"name": "Bank", "type": "bank", "code": "BANK"}
        )
        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = "online"
            journal_form.online_bank_statement_provider = "dummy"
        journal_form.save()

        self.assertTrue(journal.online_bank_statement_provider_id)
        save_provider_id = journal.online_bank_statement_provider_id.id

        # Stuff should not change when doing unrelated write.
        journal.write({"code": "BIGBANK"})
        self.assertTrue(journal.online_bank_statement_provider_id)
        self.assertEqual(journal.online_bank_statement_provider_id.id, save_provider_id)

        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = "undefined"
        journal_form.save()

        self.assertFalse(journal.online_bank_statement_provider_id)
        self.assertFalse(
            self.OnlineBankStatementProvider.search(
                [
                    ("id", "=", save_provider_id),
                ]
            )
        )

    def test_pull_mode_daily(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "daily"

        provider.with_context(step={"hours": 2})._pull(
            self.now - relativedelta(days=1),
            self.now,
        )
        self.assertEqual(
            len(self.AccountBankStatement.search([("journal_id", "=", journal.id)])), 2
        )

    def test_pull_mode_weekly(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "weekly"

        provider.with_context(step={"hours": 8})._pull(
            self.now - relativedelta(weeks=1),
            self.now,
        )
        self.assertEqual(
            len(self.AccountBankStatement.search([("journal_id", "=", journal.id)])), 2
        )

    def test_pull_mode_monthly(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "monthly"

        provider.with_context(step={"hours": 8})._pull(
            self.now - relativedelta(months=1),
            self.now,
        )
        self.assertEqual(
            len(self.AccountBankStatement.search([("journal_id", "=", journal.id)])), 2
        )

    def test_pull_scheduled(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.next_run = self.now - relativedelta(days=15)

        self.assertFalse(
            self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        )

        provider.with_context(step={"hours": 8})._scheduled_pull()

        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)

    def test_pull_skip_duplicates_by_unique_import_id(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "weekly"

        provider.with_context(
            step={"hours": 8},
            data_since=self.now - relativedelta(weeks=2),
            data_until=self.now,
        )._pull(
            self.now - relativedelta(weeks=2),
            self.now,
        )
        self.assertEqual(
            len(
                self.AccountBankStatementLine.search([("journal_id", "=", journal.id)])
            ),
            14 * (24 / 8),
        )

        provider.with_context(
            step={"hours": 8},
            data_since=self.now - relativedelta(weeks=3),
            data_until=self.now - relativedelta(weeks=1),
        )._pull(
            self.now - relativedelta(weeks=3),
            self.now - relativedelta(weeks=1),
        )
        self.assertEqual(
            len(
                self.AccountBankStatementLine.search([("journal_id", "=", journal.id)])
            ),
            21 * (24 / 8),
        )

        provider.with_context(
            step={"hours": 8},
            data_since=self.now - relativedelta(weeks=1),
            data_until=self.now,
        )._pull(
            self.now - relativedelta(weeks=1),
            self.now,
        )
        self.assertEqual(
            len(
                self.AccountBankStatementLine.search([("journal_id", "=", journal.id)])
            ),
            21 * (24 / 8),
        )

    def test_interval_type_minutes(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = "minutes"
        provider._compute_update_schedule()

    def test_interval_type_hours(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = "hours"
        provider._compute_update_schedule()

    def test_interval_type_days(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = "days"
        provider._compute_update_schedule()

    def test_interval_type_weeks(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = "weeks"
        provider._compute_update_schedule()

    def test_pull_no_crash(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "weekly"

        provider.with_context(crash=True, scheduled=True)._pull(
            self.now - relativedelta(hours=1),
            self.now,
        )
        self.assertFalse(
            self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        )

    def test_pull_crash(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "weekly"

        with self.assertRaises(Exception):
            provider.with_context(crash=True)._pull(
                self.now - relativedelta(hours=1),
                self.now,
            )

    def test_pull_httperror(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "weekly"

        with self.assertRaises(HTTPError):
            provider.with_context(
                crash=True,
                exception=HTTPError(None, 500, "Error", None, None),
            )._pull(
                self.now - relativedelta(hours=1),
                self.now,
            )

    def test_pull_no_balance(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "daily"

        provider.with_context(
            step={"hours": 2},
            balance_start=0,
            amount=100.0,
            balance=False,
        )._pull(
            self.now - relativedelta(days=1),
            self.now,
        )
        statements = self.AccountBankStatement.search(
            [("journal_id", "=", journal.id)],
            order="date asc",
        )
        self.assertFalse(statements[0].balance_start)
        self.assertTrue(statements[0].balance_end)
        self.assertTrue(statements[1].balance_start)

    def test_wizard(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )
        vals = self.OnlineBankStatementPullWizard.with_context(
            active_model="account.journal", active_id=journal.id
        ).default_get(fields_list=["provider_ids"])
        vals["date_since"] = self.now - relativedelta(hours=1)
        vals["date_until"] = self.now
        wizard = self.OnlineBankStatementPullWizard.create(vals)
        self.assertTrue(wizard.provider_ids)
        wizard.action_pull()
        self.assertTrue(
            self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        )

    def test_pull_statement_partially(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "monthly"

        provider_context = {
            "step": {"hours": 24},
            "data_since": datetime(2020, 1, 1),
            "amount": 1.0,
            "balance_start": 0,
        }

        provider.with_context(
            **provider_context,
            data_until=datetime(2020, 1, 31),
        )._pull(
            datetime(2020, 1, 1),
            datetime(2020, 1, 31),
        )
        statements = self.AccountBankStatement.search(
            [("journal_id", "=", journal.id)],
            order="date asc",
        )
        self.assertEqual(len(statements), 1)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 30.0)

        provider.with_context(
            **provider_context,
            data_until=datetime(2020, 2, 15),
        )._pull(
            datetime(2020, 1, 1),
            datetime(2020, 2, 29),
        )
        statements = self.AccountBankStatement.search(
            [("journal_id", "=", journal.id)],
            order="date asc",
        )
        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 31.0)
        self.assertEqual(statements[1].balance_start, 31.0)
        self.assertEqual(statements[1].balance_end_real, 45.0)

        provider.with_context(
            **provider_context,
            data_until=datetime(2020, 2, 29),
        )._pull(
            datetime(2020, 1, 1),
            datetime(2020, 2, 29),
        )
        statements = self.AccountBankStatement.search(
            [("journal_id", "=", journal.id)],
            order="date asc",
        )
        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[0].balance_start, 0.0)
        self.assertEqual(statements[0].balance_end_real, 31.0)
        self.assertEqual(statements[1].balance_start, 31.0)
        self.assertEqual(statements[1].balance_end_real, 59.0)

    def test_tz_utc(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.tz = "UTC"
        provider.with_context(
            step={"hours": 1},
            data_since=datetime(2020, 4, 17, 22, 0),
            data_until=datetime(2020, 4, 18, 2, 0),
            tz="UTC",
        )._pull(
            datetime(2020, 4, 17, 22, 0),
            datetime(2020, 4, 18, 2, 0),
        )

        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 2)

        lines = statement.mapped("line_ids").sorted()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 17))
        self.assertEqual(lines[1].date, date(2020, 4, 17))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def test_tz_non_utc(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.tz = "Etc/GMT-2"
        provider.with_context(
            step={"hours": 1},
            data_since=datetime(2020, 4, 17, 22, 0),
            data_until=datetime(2020, 4, 18, 2, 0),
            tz="UTC",
        )._pull(
            datetime(2020, 4, 17, 22, 0),
            datetime(2020, 4, 18, 2, 0),
        )

        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 2)

        lines = statement.mapped("line_ids").sorted()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 18))
        self.assertEqual(lines[1].date, date(2020, 4, 18))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def test_other_tz_to_utc(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.with_context(
            step={"hours": 1},
            tz="Etc/GMT-2",
            data_since=datetime(2020, 4, 18, 0, 0),
            data_until=datetime(2020, 4, 18, 4, 0),
        )._pull(
            datetime(2020, 4, 17, 22, 0),
            datetime(2020, 4, 18, 2, 0),
        )

        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 2)

        lines = statement.mapped("line_ids").sorted()
        self.assertEqual(len(lines), 4)
        self.assertEqual(lines[0].date, date(2020, 4, 17))
        self.assertEqual(lines[1].date, date(2020, 4, 17))
        self.assertEqual(lines[2].date, date(2020, 4, 18))
        self.assertEqual(lines[3].date, date(2020, 4, 18))

    def test_timestamp_date_only_date(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.with_context(step={"hours": 1}, timestamp_mode="date")._pull(
            datetime(2020, 4, 18, 0, 0),
            datetime(2020, 4, 18, 4, 0),
        )

        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)

        lines = statement.line_ids
        self.assertEqual(len(lines), 24)
        for line in lines:
            self.assertEqual(line.date, date(2020, 4, 18))

    def test_timestamp_date_only_str(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.with_context(
            step={"hours": 1},
            data_since=datetime(2020, 4, 18, 0, 0),
            data_until=datetime(2020, 4, 18, 4, 0),
            timestamp_mode="str",
        )._pull(
            datetime(2020, 4, 18, 0, 0),
            datetime(2020, 4, 18, 4, 0),
        )

        statement = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statement), 1)

        lines = statement.line_ids
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
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )
        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = "daily"
        with mock.patch(mock_obtain_statement_data) as mock_data:
            mock_data.side_effect = [
                self._get_statement_line_data(date(2021, 8, 10)),
                ([], {}),  # August 8th, doesn't have statement
                ([], {}),  # August 9th, doesn't have statement
                self._get_statement_line_data(date(2021, 8, 13)),
            ]
            provider._pull(datetime(2021, 8, 10), datetime(2021, 8, 14))
        statements = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        self.assertEqual(len(statements), 2)
        self.assertEqual(statements[1].balance_start, 0)
        self.assertEqual(statements[1].balance_end_real, 100)
        self.assertEqual(len(statements[1].line_ids), 1)
        self.assertEqual(statements[0].balance_start, 100)
        self.assertEqual(statements[0].balance_end_real, 200)
        self.assertEqual(len(statements[0].line_ids), 1)

    def test_create_empty_statements(self):
        """Test creating empty bank statements
        ('Allow empty statements' field is check at the provider level).
        """
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )
        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.allow_empty_statements = True
        provider.statement_creation_mode = "daily"
        with mock.patch(mock_obtain_statement_data) as mock_data:
            mock_data.side_effect = [
                self._get_statement_line_data(date(2021, 8, 10)),
                ([], {}),  # August 8th, doesn't have statement
                ([], {}),  # August 9th, doesn't have statement
                self._get_statement_line_data(date(2021, 8, 13)),
            ]
            provider._pull(datetime(2021, 8, 10), datetime(2021, 8, 14))
        statements = self.AccountBankStatement.search([("journal_id", "=", journal.id)])
        # 4 Statements: 2 with movements and 2 empty
        self.assertEqual(len(statements), 4)
        # With movement
        self.assertEqual(statements[3].balance_start, 0)
        self.assertEqual(statements[3].balance_end_real, 100)
        self.assertEqual(len(statements[3].line_ids), 1)
        # Empty
        self.assertEqual(statements[2].balance_start, 100)
        self.assertEqual(statements[2].balance_end_real, 100)
        self.assertEqual(len(statements[2].line_ids), 0)
        # Empty
        self.assertEqual(statements[1].balance_start, 100)
        self.assertEqual(statements[1].balance_end_real, 100)
        self.assertEqual(len(statements[1].line_ids), 0)
        # With movement
        self.assertEqual(statements[0].balance_start, 100)
        self.assertEqual(statements[0].balance_end_real, 200)
        self.assertEqual(len(statements[0].line_ids), 1)

    def test_schedule_adjustment(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "bank_statements_source": "online",
                "online_bank_statement_provider": "dummy",
            }
        )
        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = "hours"
        five_minutes_ago = self.now - relativedelta(minutes=5)
        three_hours_earlier = five_minutes_ago - relativedelta(hours=3)
        fiftyfive_minutes_later = five_minutes_ago + relativedelta(hours=1)
        provider.next_run = three_hours_earlier
        provider.last_successful_run = three_hours_earlier - relativedelta(hours=1)
        provider._scheduled_pull()
        self.assertEqual(provider.last_successful_run, five_minutes_ago)
        self.assertEqual(provider.next_run, fiftyfive_minutes_later)
