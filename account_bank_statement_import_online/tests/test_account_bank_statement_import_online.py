# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from dateutil.relativedelta import relativedelta

from psycopg2 import IntegrityError

from odoo.tests import common
from odoo.tools import mute_logger
from odoo import fields


class TestAccountBankAccountStatementImportOnline(common.TransactionCase):

    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.AccountJournal = self.env['account.journal']
        self.OnlineBankStatementProvider = self.env[
            'online.bank.statement.provider'
        ]
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementLine = self.env['account.bank.statement.line']

    def test_provider_unlink_restricted(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
        })
        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = 'online'
            journal_form.online_bank_statement_provider = 'dummy'
        journal_form.save()

        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            journal.online_bank_statement_provider_id.unlink()

    def test_cascade_unlink(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
        })
        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = 'online'
            journal_form.online_bank_statement_provider = 'dummy'
        journal_form.save()

        self.assertTrue(journal.online_bank_statement_provider_id)
        journal.unlink()
        self.assertFalse(self.OnlineBankStatementProvider.search([]))

    def test_source_change_cleanup(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
        })
        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = 'online'
            journal_form.online_bank_statement_provider = 'dummy'
        journal_form.save()

        self.assertTrue(journal.online_bank_statement_provider_id)

        with common.Form(journal) as journal_form:
            journal_form.bank_statements_source = 'undefined'
        journal_form.save()

        self.assertFalse(journal.online_bank_statement_provider_id)
        self.assertFalse(self.OnlineBankStatementProvider.search([]))

    def test_pull_boundary(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.with_context({
            'expand_by': 1,
        })._pull(
            self.now - relativedelta(hours=1),
            self.now,
        )

        statement = self.AccountBankStatement.search(
            [('journal_id', '=', journal.id)],
        )
        self.assertEquals(len(statement), 1)
        self.assertEquals(len(statement.line_ids), 12)

    def test_pull_mode_daily(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = 'daily'

        provider.with_context(step={'hours': 2})._pull(
            self.now - relativedelta(days=1),
            self.now,
        )
        self.assertEquals(
            len(self.AccountBankStatement.search(
                [('journal_id', '=', journal.id)]
            )),
            2
        )

    def test_pull_mode_weekly(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = 'weekly'

        provider.with_context(step={'hours': 8})._pull(
            self.now - relativedelta(weeks=1),
            self.now,
        )
        self.assertEquals(
            len(self.AccountBankStatement.search(
                [('journal_id', '=', journal.id)]
            )),
            2
        )

    def test_pull_mode_monthly(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = 'monthly'

        provider.with_context(step={'hours': 8})._pull(
            self.now - relativedelta(months=1),
            self.now,
        )
        self.assertEquals(
            len(self.AccountBankStatement.search(
                [('journal_id', '=', journal.id)]
            )),
            2
        )

    def test_pull_scheduled(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.next_run = (
            self.now - relativedelta(days=15)
        )

        self.assertFalse(self.AccountBankStatement.search(
            [('journal_id', '=', journal.id)],
        ))

        provider.with_context(step={'hours': 8})._scheduled_pull()

        statement = self.AccountBankStatement.search(
            [('journal_id', '=', journal.id)],
        )
        self.assertEquals(len(statement), 1)

    def test_pull_skip_duplicates_by_unique_import_id(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = 'weekly'

        provider.with_context(step={'hours': 8})._pull(
            self.now - relativedelta(weeks=2),
            self.now,
        )
        self.assertEquals(
            len(self.AccountBankStatementLine.search(
                [('journal_id', '=', journal.id)]
            )),
            14 * (24 / 8)
        )

        provider.with_context(step={'hours': 8})._pull(
            self.now - relativedelta(weeks=3),
            self.now - relativedelta(weeks=1),
        )
        self.assertEquals(
            len(self.AccountBankStatementLine.search(
                [('journal_id', '=', journal.id)]
            )),
            21 * (24 / 8)
        )

        provider.with_context(step={'hours': 8})._pull(
            self.now - relativedelta(weeks=1),
            self.now,
        )
        self.assertEquals(
            len(self.AccountBankStatementLine.search(
                [('journal_id', '=', journal.id)]
            )),
            21 * (24 / 8)
        )

    def test_interval_type_minutes(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = 'minutes'
        provider._compute_update_schedule()

    def test_interval_type_hours(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = 'hours'
        provider._compute_update_schedule()

    def test_interval_type_days(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = 'days'
        provider._compute_update_schedule()

    def test_interval_type_weeks(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.interval_type = 'weeks'
        provider._compute_update_schedule()

    def test_pull_no_crash(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = 'weekly'

        provider.with_context(
            crash=True,
            scheduled=True,
        )._pull(
            self.now - relativedelta(hours=1),
            self.now,
        )
        self.assertFalse(self.AccountBankStatement.search(
            [('journal_id', '=', journal.id)],
        ))

    def test_pull_crash(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'dummy',
        })

        provider = journal.online_bank_statement_provider_id
        provider.active = True
        provider.statement_creation_mode = 'weekly'

        with self.assertRaises(Exception):
            provider.with_context(
                crash=True,
            )._pull(
                self.now - relativedelta(hours=1),
                self.now,
            )
