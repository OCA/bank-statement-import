# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime, time, timedelta

from pytz import timezone, utc

from odoo import api, fields, models


class OnlineBankStatementCheck(models.TransientModel):
    _name = "online.bank.statement.check"
    _description = "Online Bank Statement Check"

    provider_id = fields.Many2one(
        comodel_name="online.bank.statement.provider", required=True
    )
    journal_id = fields.Many2one(related="provider_id.journal_id")
    currency_id = fields.Many2one(
        comodel_name="res.currency", compute="_compute_currency_id"
    )
    date_from = fields.Date(
        required=True, default=lambda self: fields.Date.today() - timedelta(days=30)
    )
    date_to = fields.Date(required=True, default=fields.Date.today)
    state = fields.Selection(
        selection=[("draft", "To Check"), ("done", "Checked")],
        default="draft",
        required=True,
    )
    day_ids = fields.One2many(
        comodel_name="online.bank.statement.check.day", inverse_name="check_id"
    )
    issue_ids = fields.One2many(
        comodel_name="online.bank.statement.check.issue", inverse_name="check_id"
    )
    first_mismatch_date = fields.Date(
        help="First day whose lines or balance do not match the provider."
    )
    missing_count = fields.Integer(compute="_compute_missing_count")

    @api.depends("journal_id")
    def _compute_currency_id(self):
        for check in self:
            check.currency_id = (
                check.journal_id.currency_id or check.journal_id.company_id.currency_id
            )

    @api.depends("issue_ids.issue_type")
    def _compute_missing_count(self):
        for check in self:
            check.missing_count = len(
                check.issue_ids.filtered(lambda issue: issue.issue_type == "missing")
            )

    def action_check(self):
        self.ensure_one()
        provider_lines = self._get_provider_lines()
        odoo_lines = self._get_odoo_lines(provider_lines)
        self.day_ids.unlink()
        self.issue_ids.unlink()
        self.issue_ids = [
            (0, 0, values)
            for values in self._get_issue_values(provider_lines, odoo_lines)
        ]
        self.day_ids = [
            (0, 0, values)
            for values in self._get_day_values(provider_lines, odoo_lines)
        ]
        mismatches = self.day_ids.filtered("mismatch")
        self.first_mismatch_date = mismatches[:1].date
        self.state = "done"
        return self._reopen()

    def action_import_missing(self):
        """Pull the period again: the lines already imported are skipped"""
        self.ensure_one()
        self.provider_id._pull(*self._get_utc_bounds())
        return self.action_check()

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }

    def _get_utc_bounds(self):
        """Start and end of the period, as naive UTC datetimes"""
        provider_tz = timezone(self.provider_id.tz) if self.provider_id.tz else utc
        since = provider_tz.localize(datetime.combine(self.date_from, time.min))
        until = provider_tz.localize(
            datetime.combine(self.date_to + timedelta(days=1), time.min)
        )
        return (
            since.astimezone(utc).replace(tzinfo=None),
            until.astimezone(utc).replace(tzinfo=None),
        )

    def _to_provider_date(self, value):
        """Date of a line of the provider, in the timezone of the provider"""
        if isinstance(value, str):
            value = fields.Datetime.to_datetime(value)
        if not isinstance(value, datetime):
            return value
        if value.tzinfo is None:
            value = utc.localize(value)
        provider_tz = timezone(self.provider_id.tz) if self.provider_id.tz else utc
        return value.astimezone(provider_tz).date()

    def _get_provider_lines(self):
        """Lines of the period according to the provider.

        :return: a list of dicts with the unique import id (as stored on the
            statement lines), the date, the amount and the label
        """
        provider = self.provider_id
        data = provider.with_context(account_statement_online_import_debug=True)._pull(
            *self._get_utc_bounds()
        )
        lines = []
        seen = set()
        for item in data:
            if not isinstance(item, list):
                continue  # Values of the statement
            for line in item:
                values = dict(line)
                self.journal_id._statement_line_import_update_unique_import_id(
                    values, provider.account_number
                )
                unique_import_id = values.get("unique_import_id")
                if unique_import_id and unique_import_id in seen:
                    continue
                seen.add(unique_import_id)
                line_date = self._to_provider_date(line["date"])
                if not self.date_from <= line_date <= self.date_to:
                    continue
                lines.append(
                    {
                        "unique_import_id": unique_import_id,
                        "date": line_date,
                        "amount": float(line["amount"]),
                        "payment_ref": line.get("payment_ref") or line.get("ref"),
                    }
                )
        return lines

    def _get_odoo_lines(self, provider_lines):
        """Statement lines of the period, and those of the provider lines"""
        unique_import_ids = [
            line["unique_import_id"]
            for line in provider_lines
            if line["unique_import_id"]
        ]
        return self.env["account.bank.statement.line"].search(
            [
                ("journal_id", "=", self.journal_id.id),
                "|",
                "&",
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
                ("unique_import_id", "in", unique_import_ids),
            ],
            order="date, id",
        )

    def _get_issue_values(self, provider_lines, odoo_lines):
        currency = self.currency_id
        odoo_by_id = {
            line.unique_import_id: line for line in odoo_lines if line.unique_import_id
        }
        provider_ids = set()
        issues = []
        for line in provider_lines:
            unique_import_id = line["unique_import_id"]
            if not unique_import_id:
                continue
            provider_ids.add(unique_import_id)
            values = {
                "unique_import_id": unique_import_id,
                "provider_date": line["date"],
                "provider_amount": line["amount"],
                "payment_ref": line["payment_ref"],
            }
            odoo_line = odoo_by_id.get(unique_import_id)
            if not odoo_line:
                issues.append(dict(values, issue_type="missing"))
                continue
            values.update(
                {
                    "statement_line_id": odoo_line.id,
                    "odoo_date": odoo_line.date,
                    "odoo_amount": odoo_line.amount,
                }
            )
            if currency.compare_amounts(odoo_line.amount, line["amount"]):
                issues.append(dict(values, issue_type="amount"))
            elif odoo_line.date != line["date"]:
                issues.append(dict(values, issue_type="date"))
        for odoo_line in odoo_lines:
            if odoo_line.unique_import_id in provider_ids:
                continue
            if not self.date_from <= odoo_line.date <= self.date_to:
                continue
            issues.append(
                {
                    "issue_type": "extra",
                    "unique_import_id": odoo_line.unique_import_id,
                    "statement_line_id": odoo_line.id,
                    "odoo_date": odoo_line.date,
                    "odoo_amount": odoo_line.amount,
                    "payment_ref": odoo_line.payment_ref,
                }
            )
        return issues

    def _get_day_values(self, provider_lines, odoo_lines):
        currency = self.currency_id
        statements = self.env["account.bank.statement"].search(
            [
                ("journal_id", "=", self.journal_id.id),
                ("date", ">=", self.date_from),
                ("date", "<=", self.date_to),
            ]
        )
        days = []
        cumulative = 0.0
        day = self.date_from
        while day <= self.date_to:
            provider_amount = sum(
                line["amount"] for line in provider_lines if line["date"] == day
            )
            odoo_amount = sum(
                odoo_lines.filtered(lambda line, day=day: line.date == day).mapped(
                    "amount"
                )
            )
            difference = currency.round(odoo_amount - provider_amount)
            cumulative = currency.round(cumulative + difference)
            statement = statements.filtered(
                lambda statement, day=day: statement.date == day
            )[:1]
            balance_difference = 0.0
            if statement and statement.balance_end_real:
                balance_difference = currency.round(
                    statement.balance_end - statement.balance_end_real
                )
            days.append(
                {
                    "date": day,
                    "provider_amount": provider_amount,
                    "odoo_amount": odoo_amount,
                    "difference": difference,
                    "cumulative_difference": cumulative,
                    "statement_id": statement.id,
                    "balance_difference": balance_difference,
                    "mismatch": not currency.is_zero(difference)
                    or not currency.is_zero(balance_difference),
                }
            )
            day += timedelta(days=1)
        return days


class OnlineBankStatementCheckDay(models.TransientModel):
    _name = "online.bank.statement.check.day"
    _description = "Online Bank Statement Check Day"
    _order = "date"

    check_id = fields.Many2one(
        comodel_name="online.bank.statement.check", required=True, ondelete="cascade"
    )
    currency_id = fields.Many2one(related="check_id.currency_id")
    date = fields.Date(required=True)
    provider_amount = fields.Monetary(string="Provider")
    odoo_amount = fields.Monetary(string="Odoo")
    difference = fields.Monetary()
    cumulative_difference = fields.Monetary()
    statement_id = fields.Many2one(comodel_name="account.bank.statement")
    balance_difference = fields.Monetary(
        help="Difference between the computed and the declared ending balance of "
        "the statement of the day."
    )
    mismatch = fields.Boolean()


class OnlineBankStatementCheckIssue(models.TransientModel):
    _name = "online.bank.statement.check.issue"
    _description = "Online Bank Statement Check Issue"
    _order = "provider_date, odoo_date, id"

    check_id = fields.Many2one(
        comodel_name="online.bank.statement.check", required=True, ondelete="cascade"
    )
    currency_id = fields.Many2one(related="check_id.currency_id")
    issue_type = fields.Selection(
        selection=[
            ("missing", "Missing in Odoo"),
            ("extra", "Not at the provider"),
            ("amount", "Different amount"),
            ("date", "Different date"),
        ],
        required=True,
    )
    unique_import_id = fields.Char(string="Import ID")
    payment_ref = fields.Char(string="Label")
    provider_date = fields.Date()
    provider_amount = fields.Monetary()
    odoo_date = fields.Date()
    odoo_amount = fields.Monetary()
    statement_line_id = fields.Many2one(comodel_name="account.bank.statement.line")
