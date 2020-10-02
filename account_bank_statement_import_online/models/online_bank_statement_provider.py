# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime
from dateutil.relativedelta import relativedelta, MO
from decimal import Decimal
from html import escape
import logging
from pytz import timezone, utc
from sys import exc_info

from odoo import models, fields, api, _
from odoo.addons.base.models.res_bank import sanitize_account_number
from odoo.addons.base.models.res_partner import _tz_get

_logger = logging.getLogger(__name__)


class OnlineBankStatementProvider(models.Model):
    _name = 'online.bank.statement.provider'
    _inherit = ['mail.thread']
    _description = 'Online Bank Statement Provider'

    company_id = fields.Many2one(
        related='journal_id.company_id',
        store=True,
    )
    active = fields.Boolean()
    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )
    journal_id = fields.Many2one(
        comodel_name='account.journal',
        required=True,
        readonly=True,
        ondelete='cascade',
        domain=[
            ('type', '=', 'bank'),
        ],
    )
    currency_id = fields.Many2one(
        related='journal_id.currency_id',
    )
    account_number = fields.Char(
        related='journal_id.bank_account_id.sanitized_acc_number'
    )
    tz = fields.Selection(
        selection=_tz_get,
        string='Timezone',
        default=lambda self: self.env.context.get('tz'),
        help=(
            'Timezone to convert transaction timestamps to prior being'
            ' saved into a statement.'
        ),
    )
    service = fields.Selection(
        selection=lambda self: self._selection_service(),
        required=True,
        readonly=True,
    )
    interval_type = fields.Selection(
        selection=[
            ('minutes', 'Minute(s)'),
            ('hours', 'Hour(s)'),
            ('days', 'Day(s)'),
            ('weeks', 'Week(s)'),
        ],
        default='hours',
        required=True,
    )
    interval_number = fields.Integer(
        string='Scheduled update interval',
        default=1,
        required=True,
    )
    update_schedule = fields.Char(
        string='Update Schedule',
        compute='_compute_update_schedule',
    )
    last_successful_run = fields.Datetime(
        string='Last successful pull',
    )
    next_run = fields.Datetime(
        string='Next scheduled pull',
        default=fields.Datetime.now,
        required=True,
    )
    statement_creation_mode = fields.Selection(
        selection=[
            ('daily', 'Daily statements'),
            ('weekly', 'Weekly statements'),
            ('monthly', 'Monthly statements'),
        ],
        default='daily',
        required=True,
    )
    api_base = fields.Char()
    origin = fields.Char()
    username = fields.Char()
    password = fields.Char()
    key = fields.Binary()
    certificate = fields.Binary()
    passphrase = fields.Char()
    certificate_public_key = fields.Text()
    certificate_private_key = fields.Text()
    certificate_chain = fields.Text()

    _sql_constraints = [
        (
            'journal_id_uniq',
            'UNIQUE(journal_id)',
            'Only one online banking statement provider per journal!'
        ),
        (
            'valid_interval_number',
            'CHECK(interval_number > 0)',
            'Scheduled update interval must be greater than zero!'
        )
    ]

    @api.model
    def _get_available_services(self):
        """Hook for extension"""
        return []

    @api.model
    def _selection_service(self):
        return self._get_available_services() + [('dummy', 'Dummy')]

    @api.model
    def values_service(self):
        return self._get_available_services()

    @api.multi
    @api.depends('service')
    def _compute_name(self):
        for provider in self:
            provider.name = list(filter(
                lambda x: x[0] == provider.service,
                self._selection_service()
            ))[0][1]

    @api.multi
    @api.depends('active', 'interval_type', 'interval_number')
    def _compute_update_schedule(self):
        for provider in self:
            if not provider.active:
                provider.update_schedule = _('Inactive')
                continue

            provider.update_schedule = _('%(number)s %(type)s') % {
                'number': provider.interval_number,
                'type': list(filter(
                    lambda x: x[0] == provider.interval_type,
                    self._fields['interval_type'].selection
                ))[0][1],
            }

    @api.multi
    def _pull(self, date_since, date_until):
        AccountBankStatement = self.env['account.bank.statement']
        is_scheduled = self.env.context.get('scheduled')
        if is_scheduled:
            AccountBankStatement = AccountBankStatement.with_context(
                tracking_disable=True,
            )
        AccountBankStatementLine = self.env['account.bank.statement.line']
        for provider in self:
            provider_tz = timezone(provider.tz) if provider.tz else utc
            statement_date_since = provider._get_statement_date_since(
                date_since
            )
            while statement_date_since < date_until:
                statement_date_until = (
                    statement_date_since + provider._get_statement_date_step()
                )
                try:
                    data = provider._obtain_statement_data(
                        statement_date_since,
                        statement_date_until
                    )
                except:
                    if is_scheduled:
                        _logger.warning(
                            'Online Bank Statement Provider "%s" failed to'
                            ' obtain statement data since %s until %s' % (
                                provider.name,
                                statement_date_since,
                                statement_date_until,
                            ),
                            exc_info=True,
                        )
                        provider.message_post(
                            body=_(
                                'Failed to obtain statement data for period '
                                'since %s until %s: %s. See server logs for '
                                'more details.'
                            ) % (
                                statement_date_since,
                                statement_date_until,
                                escape(str(exc_info()[1])) or _('N/A')
                            ),
                            subject=_(
                                'Issue with Online Bank Statement Provider'
                            ),
                        )
                        break
                    raise
                statement_date = provider._get_statement_date(
                    statement_date_since,
                    statement_date_until,
                )
                if not data:
                    data = ([], {})
                lines_data, statement_values = data
                if not lines_data:
                    lines_data = []
                if not statement_values:
                    statement_values = {}
                statement = AccountBankStatement.search([
                    ('journal_id', '=', provider.journal_id.id),
                    ('state', '=', 'open'),
                    ('date', '=', statement_date),
                ], limit=1)
                if not statement:
                    statement_values.update({
                        'name': provider.journal_id.sequence_id.with_context(
                            ir_sequence_date=statement_date,
                        ).next_by_id(),
                        'journal_id': provider.journal_id.id,
                        'date': statement_date,
                    })
                    statement = AccountBankStatement.with_context(
                        journal_id=provider.journal_id.id,
                    ).create(
                        # NOTE: This is needed since create() alters values
                        statement_values.copy()
                    )
                filtered_lines = []
                for line_values in lines_data:
                    date = line_values['date']
                    if not isinstance(date, datetime):
                        date = fields.Datetime.from_string(date)

                    if date.tzinfo is None:
                        date = date.replace(tzinfo=utc)
                    date = date.astimezone(utc).replace(tzinfo=None)

                    if date < statement_date_since:
                        if 'balance_start' in statement_values:
                            statement_values['balance_start'] = (
                                Decimal(
                                    statement_values['balance_start']
                                ) + Decimal(
                                    line_values['amount']
                                )
                            )
                        continue
                    elif date >= statement_date_until:
                        if 'balance_end_real' in statement_values:
                            statement_values['balance_end_real'] = (
                                Decimal(
                                    statement_values['balance_end_real']
                                ) - Decimal(
                                    line_values['amount']
                                )
                            )
                        continue

                    date = date.replace(tzinfo=utc)
                    date = date.astimezone(provider_tz).replace(tzinfo=None)
                    line_values['date'] = date

                    unique_import_id = line_values.get('unique_import_id')
                    if unique_import_id:
                        unique_import_id = provider._generate_unique_import_id(
                            unique_import_id
                        )
                        line_values.update({
                            'unique_import_id': unique_import_id,
                        })
                        if AccountBankStatementLine.sudo().search(
                                [('unique_import_id', '=', unique_import_id)],
                                limit=1):
                            continue

                    bank_account_number = line_values.get('account_number')
                    if bank_account_number:
                        line_values.update({
                            'account_number': (
                                self._sanitize_bank_account_number(
                                    bank_account_number
                                )
                            ),
                        })

                    filtered_lines.append(line_values)
                statement_values.update({
                    'line_ids': [[0, False, line] for line in filtered_lines],
                })
                if 'balance_start' in statement_values:
                    statement_values['balance_start'] = float(
                        statement_values['balance_start']
                    )
                if 'balance_end_real' in statement_values:
                    statement_values['balance_end_real'] = float(
                        statement_values['balance_end_real']
                    )
                statement.write(statement_values)
                statement_date_since = statement_date_until
            if is_scheduled:
                provider._schedule_next_run()

    @api.multi
    def _schedule_next_run(self):
        self.ensure_one()
        self.last_successful_run = self.next_run
        self.next_run += self._get_next_run_period()

    @api.multi
    def _get_statement_date_since(self, date):
        self.ensure_one()
        date = date.replace(
            hour=0,
            minute=0,
            second=0,
            microsecond=0,
        )
        if self.statement_creation_mode == 'daily':
            return date
        elif self.statement_creation_mode == 'weekly':
            return date + relativedelta(weekday=MO(-1))
        elif self.statement_creation_mode == 'monthly':
            return date.replace(
                day=1,
            )

    @api.multi
    def _get_statement_date_step(self):
        self.ensure_one()
        if self.statement_creation_mode == 'daily':
            return relativedelta(
                days=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        elif self.statement_creation_mode == 'weekly':
            return relativedelta(
                weeks=1,
                weekday=MO,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        elif self.statement_creation_mode == 'monthly':
            return relativedelta(
                months=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

    @api.multi
    def _get_statement_date(self, date_since, date_until):
        self.ensure_one()
        # NOTE: Statement date is treated by Odoo as start of period. Details
        #  - addons/account/models/account_journal_dashboard.py
        #  - def get_line_graph_datas()
        tz = timezone(self.tz) if self.tz else utc
        date_since = date_since.replace(tzinfo=utc).astimezone(tz)
        return date_since.date()

    @api.multi
    def _generate_unique_import_id(self, unique_import_id):
        self.ensure_one()
        return (
            self.account_number and self.account_number + '-' or ''
        ) + str(self.journal_id.id) + '-' + unique_import_id

    @api.multi
    def _sanitize_bank_account_number(self, bank_account_number):
        """Hook for extension"""
        self.ensure_one()
        return sanitize_account_number(bank_account_number)

    @api.multi
    def _get_next_run_period(self):
        self.ensure_one()
        if self.interval_type == 'minutes':
            return relativedelta(minutes=self.interval_number)
        elif self.interval_type == 'hours':
            return relativedelta(hours=self.interval_number)
        elif self.interval_type == 'days':
            return relativedelta(days=self.interval_number)
        elif self.interval_type == 'weeks':
            return relativedelta(weeks=self.interval_number)

    @api.model
    def _scheduled_pull(self):
        _logger.info('Scheduled pull of online bank statements...')

        providers = self.search([
            ('active', '=', True),
            ('next_run', '<=', fields.Datetime.now()),
        ])
        if providers:
            _logger.info('Pulling online bank statements of: %s' % ', '.join(
                providers.mapped('journal_id.name')
            ))
            for provider in providers.with_context({'scheduled': True}):
                date_since = (
                    provider.last_successful_run
                ) if provider.last_successful_run else (
                    provider.next_run - provider._get_next_run_period()
                )
                date_until = provider.next_run
                provider._pull(date_since, date_until)

        _logger.info('Scheduled pull of online bank statements complete.')

    @api.multi
    def _obtain_statement_data(
        self, date_since, date_until
    ):
        """Hook for extension"""
        # Check tests/online_bank_statement_provider_dummy.py for reference
        self.ensure_one()
        return []
