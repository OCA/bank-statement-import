# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import date, datetime
from urllib.error import HTTPError

from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError

from odoo import fields
from odoo.tests import common
from odoo.tools import mute_logger


class TestAccountBankAccountStatementImportOnline(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.AccountJournal = self.env["account.journal"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.OnlineBankStatementPullWizard = self.env[
            "online.bank.statement.pull.wizard"
        ]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

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
