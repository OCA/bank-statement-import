# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com).
# Copyright 2022 Therp BV (https://therp.nl).
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
    _name = "online.bank.statement.provider"
    _inherit = ["mail.thread"]
    _description = "Online Bank Statement Provider"

    company_id = fields.Many2one(
        related="journal_id.company_id",
        store=True,
    )
    active = fields.Boolean()
    name = fields.Char(
        string="Name",
        compute="_compute_name",
        store=True,
    )
    journal_id = fields.Many2one(
        comodel_name="account.journal",
        required=True,
        ondelete="cascade",
        domain=[
            ("type", "=", "bank"),
        ],
    )
    currency_id = fields.Many2one(
        related="journal_id.currency_id",
    )
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
    allow_empty_statements = fields.Boolean()

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
    def create(self, vals):
        """Set provider_id on journal after creation."""
        records = super().create(vals)
        records._update_journals()
        return records

    @api.multi
    def write(self, vals):
        """Set provider_id on journal after creation."""
        result = super().write(vals)
        self._update_journals()
        return result

    def _update_journals(self):
        """Update journal with this provider.

        This is for compatibility reasons.
        """
        for this in self:
            this.journal_id.write(
                {
                    "online_bank_statement_provider_id": this.id,
                    "bank_statements_source": "online",
                }
            )

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

    @api.multi
    @api.depends("service")
    def _compute_name(self):
        for provider in self:
            provider.name = list(
                filter(lambda x: x[0] == provider.service, self._selection_service())
            )[0][1]

    @api.multi
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

    @api.multi
    def _pull(self, date_since, date_until):
        is_scheduled = self.env.context.get("scheduled")
        for provider in self:
            statement_date_since = provider._get_statement_date_since(date_since)
            while statement_date_since < date_until:
                # Note that statement_date_until is exclusive, while date_until is
                # inclusive. So if we have daily statements date_until might
                # be 2020-01-31, while statement_date_until is 2020-02-01.
                statement_date_until = (
                    statement_date_since + provider._get_statement_date_step()
                )
                try:
                    data = provider._retrieve_data(
                        statement_date_since, statement_date_until
                    )
                except:
                    # For scheduled pull, continue with next provider.
                    if is_scheduled:
                        break
                    raise
                provider._create_or_update_statement(
                    data, statement_date_since, statement_date_until
                )
                statement_date_since = statement_date_until
            if is_scheduled:
                provider._schedule_next_run()

    @api.multi
    def _retrieve_data(self, statement_date_since, statement_date_until):
        """Retrieve data from online provider."""
        self.ensure_one()
        try:
            data = self._obtain_statement_data(
                statement_date_since, statement_date_until
            )
            return data
        except:
            _logger.warning(
                'Online Bank Statement self "%s" failed to'
                " obtain statement data since %s until %s"
                % (
                    self.name,
                    statement_date_since,
                    statement_date_until,
                ),
                exc_info=True,
            )
            self.message_post(
                body=_(
                    "Failed to obtain statement data for period "
                    "since %s until %s: %s. See server logs for "
                    "more details."
                )
                % (
                    statement_date_since,
                    statement_date_until,
                    escape(str(exc_info()[1])) or _("N/A"),
                ),
                subject=_("Issue with Online Bank Statement self"),
            )
            raise

    def _create_or_update_statement(
        self, data, statement_date_since, statement_date_until
    ):
        """Process data retrieved from online provider."""
        self.ensure_one()
        statement_date = self._get_statement_date(
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
        if (
            not lines_data
            and not statement_values
            and not self.allow_empty_statements
        ):
            # Continue with next possible statement.
            return
        self._update_statement_balance_values(
            statement_values,
            lines_data,
            statement_date_since,
            statement_date_until
        )
        filtered_lines = self._get_filtered_lines(
            lines_data,
            statement_date_since,
            statement_date_until
        )
        self._update_line_values(filtered_lines)
        self._create_statement(statement_values, statement_date, filtered_lines)

    @api.multi
    def _create_statement(self, statement_values, statement_date, lines_data):
        """Search existing or make new statement."""
        self.ensure_one()
        AccountBankStatement = self.env["account.bank.statement"]
        domain = [
            ("journal_id", "=", self.journal_id.id),
            ("date", "=", statement_date),
        ]
        # If we have no data, we will not create a statement for the same date.
        if not lines_data:
            statement = AccountBankStatement.search(domain, limit=1)
            if statement:
                return
        # If we get here, we need to update existing or create new statement.
        statement_values.update(
            {
                "line_ids": [[0, False, line] for line in lines_data],
            }
        )
        domain.append(("state", "=", "open"))
        statement = AccountBankStatement.search(domain, limit=1)
        if statement:
            statement.write(statement_values)
        else:
            statement_values.update(
                {
                    "name": self.journal_id.sequence_id.with_context(
                        ir_sequence_date=statement_date,
                    ).next_by_id(),
                    "journal_id": self.journal_id.id,
                    "date": statement_date,
                }
            )
            statement = AccountBankStatement.with_context(
                journal_id=self.journal_id.id,
            ).create(statement_values)

    def _update_statement_balance_values(
        self,
        statement_values,
        lines_data,
        statement_date_since,
        statement_date_until
    ):
        """Update statement start or end balance from line data.

        Statements retrieved and statements created might have different begin
        and end dates. Suppose we retrieve data that covers three days, and has four
        transactions, but the statement to be created is for only one day. like this:
        statement_values: {
            "balance_start": 25.00,
            "balance_end_real": 150.00,
        }
        lines_data = [
            {"date": "2020-02-01", "amount": 25.00},
            {"date": "2020-02-02", "amount": 25.00},
            {"date": "2020-02-02", "amount": 50.00},
            {"date": "2020-02-03", "amount": 25.00},
        ]
        If we create a statement for only the day 2020-02-02, the first and
        the last line should not belong to this statement. But at the start of
        2020-02-02 the balance was 50.00. So the amounts for lesser dates should
        be added to the balance_start. Similarly amounts from later dates should
        be subtracted from balance_end_real. Which should be 125.00 for
        2020-02-02.
        """
        for line_values in lines_data:
            date = self._get_utc_line_date(line_values)
            date = date.astimezone(utc).replace(tzinfo=None)
            # Add amounts from dates before statement to balance_start.
            if date < statement_date_since:
                if "balance_start" in statement_values:
                    statement_values["balance_start"] = Decimal(
                        statement_values["balance_start"]
                    ) + Decimal(line_values["amount"])
                continue
            # Subtract amounts from dates after statement from balace_end_real.
            if date >= statement_date_until:
                if "balance_end_real" in statement_values:
                    statement_values["balance_end_real"] = Decimal(
                        statement_values["balance_end_real"]
                    ) - Decimal(line_values["amount"])
                continue
        if "balance_start" in statement_values:
            statement_values["balance_start"] = float(statement_values["balance_start"])
        if "balance_end_real" in statement_values:
            statement_values["balance_end_real"] = float(
                statement_values["balance_end_real"]
            )

    @api.multi
    def _get_filtered_lines(
        self,
        lines_data,
        statement_date_since,
        statement_date_until
    ):
        """Use unique import id to prevent duplicate lines."""
        AccountBankStatementLine = self.env["account.bank.statement.line"]
        filtered_lines = []
        for line_values in lines_data:
            # Do not include transactions for dates not in statement period.
            date = self._get_utc_line_date(line_values)
            date = date.astimezone(utc).replace(tzinfo=None)
            if date < statement_date_since:
                continue
            if date >= statement_date_until:
                continue
            # Do not include transactions already imported.
            unique_import_id = line_values.get("unique_import_id")
            if unique_import_id:
                unique_import_id = self._generate_unique_import_id(unique_import_id)
                line_values.update(
                    {
                        "unique_import_id": unique_import_id,
                    }
                )
                if AccountBankStatementLine.sudo().search(
                    [("unique_import_id", "=", unique_import_id)], limit=1
                ):
                    continue
            filtered_lines.append(line_values)
        return filtered_lines

    @api.multi
    def _update_line_values(self, lines_data):
        """Enhance data in lines."""
        self.ensure_one()
        povider_tz = timezone(self.tz) if self.tz else utc
        for line_values in lines_data:
            date = self._get_utc_line_date(line_values)
            date = date.astimezone(povider_tz).replace(tzinfo=None)
            line_values["date"] = date
            bank_account_number = line_values.get("account_number")
            if bank_account_number:
                line_values.update(
                    {
                        "account_number": (
                            self._sanitize_bank_account_number(bank_account_number)
                        ),
                    }
                )

    def _get_utc_line_date(self, line_values):
        """Convert date in line to utc date."""
        date = line_values["date"]
        if not isinstance(date, datetime):
            date = fields.Datetime.from_string(date)
        if date.tzinfo is None:
            date = date.replace(tzinfo=utc)
        return date

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
        if self.statement_creation_mode == "daily":
            return date
        elif self.statement_creation_mode == "weekly":
            return date + relativedelta(weekday=MO(-1))
        elif self.statement_creation_mode == "monthly":
            return date.replace(
                day=1,
            )

    @api.multi
    def _get_statement_date_step(self):
        self.ensure_one()
        if self.statement_creation_mode == "daily":
            return relativedelta(
                days=1,
                hour=0,
                minute=0,
                second=0,
                microsecond=0,
            )
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
            (self.account_number and self.account_number + "-" or "")
            + str(self.journal_id.id)
            + "-"
            + unique_import_id
        )

    @api.multi
    def _sanitize_bank_account_number(self, bank_account_number):
        """Hook for extension"""
        self.ensure_one()
        return sanitize_account_number(bank_account_number)

    @api.multi
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
            [
                ("active", "=", True),
                ("next_run", "<=", fields.Datetime.now()),
            ]
        )
        if providers:
            _logger.info(
                "Pulling online bank statements of: %s"
                % ", ".join(providers.mapped("journal_id.name"))
            )
            for provider in providers.with_context(
                scheduled=True,
                tracking_disable=True
            ):
                date_since = (
                    (provider.last_successful_run)
                    if provider.last_successful_run
                    else (provider.next_run - provider._get_next_run_period())
                )
                date_until = provider.next_run
                provider._pull(date_since, date_until)
        _logger.info("Scheduled pull of online bank statements complete.")

    @api.multi
    def _obtain_statement_data(self, date_since, date_until):
        """Hook for extension"""
        # Check tests/online_bank_statement_provider_dummy.py for reference
        self.ensure_one()
        return []

    def action_online_bank_statements_pull_wizard(self):
        self.ensure_one()
        WIZARD_MODEL = "online.bank.statement.pull.wizard"
        wizard = self.env[WIZARD_MODEL].create([{"provider_ids": [(6, 0, [self.id])]}])
        return {
            "type": "ir.actions.act_window",
            "res_model": WIZARD_MODEL,
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }
