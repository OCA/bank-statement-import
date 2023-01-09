# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging
from datetime import datetime
from decimal import Decimal
from html import escape

from dateutil.relativedelta import MO, relativedelta
from pytz import timezone, utc

from odoo import _, api, fields, models

from odoo.addons.base.models.res_partner import _tz_get

_logger = logging.getLogger(__name__)


class OnlineBankStatementProvider(models.Model):
    _name = "online.bank.statement.provider"
    _inherit = ["mail.thread"]
    _description = "Online Bank Statement Provider"

    company_id = fields.Many2one(related="journal_id.company_id", store=True)
    active = fields.Boolean(default=True)
    name = fields.Char(string="Name", compute="_compute_name", store=True)
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        required=True,
        readonly=True,
        ondelete="cascade",
        domain=[("type", "=", "bank")],
    )
    currency_id = fields.Many2one(related="journal_id.currency_id")
    account_number = fields.Char(
        related="journal_id.bank_account_id.sanitized_acc_number"
    )
    tz = fields.Selection(
        selection=_tz_get,
        string="Timezone",
        default=lambda self: self.env.context.get("tz"),
        help=(
            "Timezone to convert transaction timestamps to prior being"
            " saved into a statement."
        ),
    )
    service = fields.Selection(
        selection=lambda self: self._selection_service(),
        required=True,
        readonly=True,
    )
    interval_type = fields.Selection(
        selection=[
            ("minutes", "Minute(s)"),
            ("hours", "Hour(s)"),
            ("days", "Day(s)"),
            ("weeks", "Week(s)"),
        ],
        default="hours",
        required=True,
    )
    interval_number = fields.Integer(
        string="Scheduled update interval",
        default=1,
        required=True,
    )
    update_schedule = fields.Char(
        string="Update Schedule",
        compute="_compute_update_schedule",
    )
    last_successful_run = fields.Datetime(
        string="Last successful pull",
        readonly=True,
    )
    next_run = fields.Datetime(
        string="Next scheduled pull",
        default=fields.Datetime.now,
        required=True,
    )
    statement_creation_mode = fields.Selection(
        selection=[
            ("daily", "Daily statements"),
            ("weekly", "Weekly statements"),
            ("monthly", "Monthly statements"),
        ],
        default="daily",
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
    allow_empty_statements = fields.Boolean(string="Allow empty statements")

    _sql_constraints = [
        (
            "journal_id_uniq",
            "UNIQUE(journal_id)",
            "Only one online banking statement provider per journal!",
        ),
        (
            "valid_interval_number",
            "CHECK(interval_number > 0)",
            "Scheduled update interval must be greater than zero!",
        ),
    ]

    @api.model
    def _get_available_services(self):
        """Hook for extension"""
        return []

    @api.model
    def _selection_service(self):
        return self._get_available_services() + [("dummy", "Dummy")]

    @api.model
    def values_service(self):
        return self._get_available_services()

    @api.depends("service", "journal_id.name")
    def _compute_name(self):
        """We can have multiple providers/journals for the same service."""
        for provider in self:
            provider.name = " ".join([provider.journal_id.name, provider.service])

    @api.depends("active", "interval_type", "interval_number")
    def _compute_update_schedule(self):
        for provider in self:
            if not provider.active:
                provider.update_schedule = _("Inactive")
                continue

            provider.update_schedule = _("%(number)s %(type)s") % {
                "number": provider.interval_number,
                "type": list(
                    filter(
                        lambda x: x[0] == provider.interval_type,
                        self._fields["interval_type"].selection,
                    )
                )[0][1],
            }

    def _pull(self, date_since, date_until):
        is_scheduled = self.env.context.get("scheduled")
        for provider in self:
            statement_date_since = provider._get_statement_date_since(date_since)
            while statement_date_since < date_until:
                statement_date_until = (
                    statement_date_since + provider._get_statement_date_step()
                )
                try:
                    data = provider._obtain_statement_data(
                        statement_date_since, statement_date_until
                    )
                except BaseException as e:
                    if is_scheduled:
                        _logger.warning(
                            'Online Bank Statement Provider "%s" failed to'
                            " obtain statement data since %s until %s"
                            % (
                                provider.name,
                                statement_date_since,
                                statement_date_until,
                            ),
                            exc_info=True,
                        )
                        provider.message_post(
                            body=_(
                                "Failed to obtain statement data for period "
                                "since %s until %s: %s. See server logs for "
                                "more details."
                            )
                            % (
                                statement_date_since,
                                statement_date_until,
                                escape(str(e)) or _("N/A"),
                            ),
                            subject=_("Issue with Online Bank Statement Provider"),
                        )
                        break
                    raise
                provider._create_or_update_statement(
                    data, statement_date_since, statement_date_until
                )
                statement_date_since = statement_date_until
            if is_scheduled:
                provider._schedule_next_run()

    def _create_or_update_statement(
        self, data, statement_date_since, statement_date_until
    ):
        """Create or update bank statement with the data retrieved from provider."""
        self.ensure_one()
        AccountBankStatement = self.env["account.bank.statement"]
        is_scheduled = self.env.context.get("scheduled")
        if is_scheduled:
            AccountBankStatement = AccountBankStatement.with_context(
                tracking_disable=True,
            )
        if not data:
            data = ([], {})
        if not data[0] and not data[1] and not self.allow_empty_statements:
            return
        lines_data, statement_values = data
        if not lines_data:
            lines_data = []
        if not statement_values:
            statement_values = {}
        statement_date = self._get_statement_date(
            statement_date_since,
            statement_date_until,
        )
        statement = AccountBankStatement.search(
            [
                ("journal_id", "=", self.journal_id.id),
                ("state", "=", "open"),
                ("date", "=", statement_date),
            ],
            limit=1,
        )
        if not statement:
            statement_values.update(
                {
                    "name": "%s/%s"
                    % (self.journal_id.code, statement_date.strftime("%Y-%m-%d")),
                    "journal_id": self.journal_id.id,
                    "date": statement_date,
                }
            )
            statement = AccountBankStatement.with_context(
                journal_id=self.journal_id.id,
            ).create(
                # NOTE: This is needed since create() alters values
                statement_values.copy()
            )
        filtered_lines = self._get_statement_filtered_lines(
            lines_data, statement_values, statement_date_since, statement_date_until
        )
        statement_values.update(
            {"line_ids": [[0, False, line] for line in filtered_lines]}
        )
        if "balance_start" in statement_values:
            statement_values["balance_start"] = float(statement_values["balance_start"])
        if "balance_end_real" in statement_values:
            statement_values["balance_end_real"] = float(
                statement_values["balance_end_real"]
            )
        statement.write(statement_values)

    def _get_statement_filtered_lines(
        self, lines_data, statement_values, statement_date_since, statement_date_until
    ):
        """Get lines from line data, but only for the right date."""
        AccountBankStatementLine = self.env["account.bank.statement.line"]
        provider_tz = timezone(self.tz) if self.tz else utc
        journal = self.journal_id
        speeddict = journal._statement_line_import_speeddict()
        filtered_lines = []
        for line_values in lines_data:
            date = line_values["date"]
            if not isinstance(date, datetime):
                date = fields.Datetime.from_string(date)
            if date.tzinfo is None:
                date = date.replace(tzinfo=utc)
            date = date.astimezone(utc).replace(tzinfo=None)
            if date < statement_date_since:
                if "balance_start" in statement_values:
                    statement_values["balance_start"] = Decimal(
                        statement_values["balance_start"]
                    ) + Decimal(line_values["amount"])
                continue
            elif date >= statement_date_until:
                if "balance_end_real" in statement_values:
                    statement_values["balance_end_real"] = Decimal(
                        statement_values["balance_end_real"]
                    ) - Decimal(line_values["amount"])
                continue
            date = date.replace(tzinfo=utc)
            date = date.astimezone(provider_tz).replace(tzinfo=None)
            line_values["date"] = date
            journal._statement_line_import_update_unique_import_id(
                line_values, self.account_number
            )
            unique_import_id = line_values.get("unique_import_id")
            if unique_import_id:
                if AccountBankStatementLine.sudo().search(
                    [("unique_import_id", "=", unique_import_id)], limit=1
                ):
                    continue
            if not line_values.get("payment_ref"):
                line_values["payment_ref"] = line_values.get("ref")
            journal._statement_line_import_update_hook(line_values, speeddict)
            filtered_lines.append(line_values)
        return filtered_lines

    def _schedule_next_run(self):
        self.ensure_one()
        self.last_successful_run = self.next_run
        self.next_run += self._get_next_run_period()

    def _get_statement_date_since(self, date):
        self.ensure_one()
        date = date.replace(hour=0, minute=0, second=0, microsecond=0)
        if self.statement_creation_mode == "daily":
            return date
        elif self.statement_creation_mode == "weekly":
            return date + relativedelta(weekday=MO(-1))
        elif self.statement_creation_mode == "monthly":
            return date.replace(day=1)

    def _get_statement_date_step(self):
        self.ensure_one()
        if self.statement_creation_mode == "daily":
            return relativedelta(days=1, hour=0, minute=0, second=0, microsecond=0)
        elif self.statement_creation_mode == "weekly":
            return relativedelta(
                weeks=1,
                weekday=MO,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
        elif self.statement_creation_mode == "monthly":
            return relativedelta(
                months=1,
                day=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )

    def _get_statement_date(self, date_since, date_until):
        self.ensure_one()
        # NOTE: Statement date is treated by Odoo as start of period. Details
        #  - addons/account/models/account_journal_dashboard.py
        #  - def get_line_graph_datas()
        tz = timezone(self.tz) if self.tz else utc
        date_since = date_since.replace(tzinfo=utc).astimezone(tz)
        return date_since.date()

    def _get_next_run_period(self):
        self.ensure_one()
        if self.interval_type == "minutes":
            return relativedelta(minutes=self.interval_number)
        elif self.interval_type == "hours":
            return relativedelta(hours=self.interval_number)
        elif self.interval_type == "days":
            return relativedelta(days=self.interval_number)
        elif self.interval_type == "weeks":
            return relativedelta(weeks=self.interval_number)

    @api.model
    def _scheduled_pull(self):
        _logger.info("Scheduled pull of online bank statements...")

        providers = self.search(
            [("active", "=", True), ("next_run", "<=", fields.Datetime.now())]
        )
        if providers:
            _logger.info(
                "Pulling online bank statements of: %s"
                % ", ".join(providers.mapped("journal_id.name"))
            )
            for provider in providers.with_context(scheduled=True):
                provider._adjust_schedule()
                date_since = (
                    (provider.last_successful_run)
                    if provider.last_successful_run
                    else (provider.next_run - provider._get_next_run_period())
                )
                date_until = provider.next_run
                provider._pull(date_since, date_until)

        _logger.info("Scheduled pull of online bank statements complete.")

    def _adjust_schedule(self):
        """Make sure next_run is current.

        Current means adding one more period would put if after the
        current moment. This will be done at the end of the run.
        The net effect of this method and the adjustment after the run
        will be for the next_run to be in the future.
        """
        self.ensure_one()
        delta = self._get_next_run_period()
        now = datetime.now()
        next_run = self.next_run + delta
        while next_run < now:
            self.next_run = next_run
            next_run = self.next_run + delta

    def _obtain_statement_data(self, date_since, date_until):
        """Hook for extension"""
        # Check tests/online_bank_statement_provider_dummy.py for reference
        self.ensure_one()
        return []
