# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from random import randrange

from dateutil.relativedelta import relativedelta
from pytz import timezone

from odoo import fields, models


class OnlineBankStatementProviderDummy(models.Model):
    _inherit = "online.bank.statement.provider"

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "dummy":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        if self.env.context.get("crash", False):
            exception = self.env.context.get("exception", Exception("Expected"))
            raise exception

        line_step_options = self.env.context.get("step", {"minutes": 5})
        line_step = relativedelta(**line_step_options)
        expand_by = self.env.context.get("expand_by", 0)
        data_since = self.env.context.get("data_since", date_since)
        data_until = self.env.context.get("data_until", date_until)
        data_since -= expand_by * line_step
        data_until += expand_by * line_step

        balance_start = self.env.context.get(
            "balance_start", randrange(-10000, 10000, 1) * 0.1
        )
        balance = balance_start

        tz = self.env.context.get("tz")
        if tz:
            tz = timezone(tz)

        timestamp_mode = self.env.context.get("timestamp_mode")

        lines = []
        date = data_since
        while date < data_until:
            amount = self.env.context.get("amount", randrange(-100, 100, 1) * 0.1)
            transaction_date = date.replace(tzinfo=tz)
            if timestamp_mode == "date":
                transaction_date = transaction_date.date()
            elif timestamp_mode == "str":
                transaction_date = fields.Datetime.to_string(transaction_date)
            lines.append(
                {
                    "payment_ref": "payment",
                    "amount": amount,
                    "date": transaction_date,
                    "unique_import_id": str(
                        int((date - datetime(1970, 1, 1)) / timedelta(seconds=1))
                    ),
                    "partner_name": "John Doe",
                    "account_number": "XX00 0000 0000 0000",
                }
            )
            balance += amount
            date += line_step
        balance_end = balance
        statement = {}
        if self.env.context.get("balance", True):
            statement.update(
                {"balance_start": balance_start, "balance_end_real": balance_end}
            )
        return lines, statement
