# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from random import randrange

from odoo import models, api


class OnlineBankStatementProviderDummy(models.Model):
    _inherit = 'online.bank.statement.provider'

    @api.multi
    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != 'dummy':
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )  # pragma: no cover

        if self.env.context.get('crash', False):
            exception = self.env.context.get(
                'exception',
                Exception('Expected')
            )
            raise exception

        line_step_options = self.env.context.get('step', {
            'minutes': 5,
        })
        line_step = relativedelta(**line_step_options)
        expand_by = self.env.context.get('expand_by', 0)
        date_since -= expand_by * line_step
        date_until += expand_by * line_step

        balance_start = randrange(-10000, 10000, 1) * 0.1
        balance = balance_start
        lines = []
        date = date_since
        while date < date_until:
            amount = randrange(-100, 100, 1) * 0.1
            lines.append({
                'name': 'payment',
                'amount': amount,
                'date': date,
                'unique_import_id': str(int(
                    (date - datetime(1970, 1, 1)) / timedelta(seconds=1)
                )),
            })
            balance += amount
            date += line_step
        balance_end = balance
        return lines, {
            'balance_start': balance_start,
            'balance_end_real': balance_end,
        }
