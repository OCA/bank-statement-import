# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models

from dateutil.relativedelta import relativedelta, MO
from decimal import Decimal


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    import_mode = fields.Selection(
        selection=[
            ('single', 'Single statement'),
            ('daily', 'Daily statements'),
            ('weekly', 'Weekly statements'),
            ('monthly', 'Monthly statements'),
        ],
        default='single',
    )

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        stmts_vals = super()._complete_stmts_vals(
            stmts_vals,
            journal,
            account_number
        )
        if not self.import_mode or self.import_mode == 'single':
            return stmts_vals
        statements = []
        for st_vals in stmts_vals:
            transactions = list(sorted(
                map(
                    lambda transaction: self._prepare_transaction(
                        transaction
                    ),
                    st_vals['transactions']
                ),
                key=lambda transaction: transaction['date']
            ))
            if not transactions:
                continue
            del st_vals['transactions']

            balance_start = Decimal(st_vals['balance_start']) \
                if 'balance_start' in st_vals else None
            balance_end = Decimal(st_vals['balance_end_real']) \
                if 'balance_end_real' in st_vals else None
            statement_date_since = self._get_statement_date_since(
                transactions[0]['date']
            )
            while transactions:
                statement_date_until = (
                    statement_date_since + self._get_statement_date_step()
                )

                last_transaction_index = None
                for index, transaction in enumerate(transactions):
                    if transaction['date'] >= statement_date_until:
                        break
                    last_transaction_index = index
                if last_transaction_index is None:
                    # NOTE: No transactions for current period
                    statement_date_since = statement_date_until
                    continue

                statement_transactions = \
                    transactions[0:last_transaction_index + 1]
                transactions = transactions[last_transaction_index + 1:]

                statement_values = dict(st_vals)
                statement_values.update({
                    'name': self._get_statement_name(
                        journal,
                        statement_date_since,
                        statement_date_until,
                    ),
                    'date': self._get_statement_date(
                        statement_date_since,
                        statement_date_until,
                    ),
                    'transactions': statement_transactions,
                })
                if balance_start is not None:
                    statement_values.update({
                        'balance_start': float(balance_start),
                    })
                    for transaction in statement_transactions:
                        balance_start += Decimal(transaction['amount'])
                if balance_end is not None:
                    statement_balance_end = balance_end
                    for transaction in transactions:
                        statement_balance_end -= Decimal(transaction['amount'])
                    statement_values.update({
                        'balance_end_real': float(statement_balance_end),
                    })

                statements.append(statement_values)
                statement_date_since = statement_date_until
        return statements

    @api.multi
    def _prepare_transaction(self, transaction):
        transaction.update({
            'date': fields.Date.from_string(transaction['date']),
        })
        return transaction

    @api.multi
    def _get_statement_date_since(self, date):
        self.ensure_one()
        if self.import_mode == 'daily':
            return date
        elif self.import_mode == 'weekly':
            return date + relativedelta(weekday=MO(-1))
        elif self.import_mode == 'monthly':
            return date.replace(
                day=1,
            )

    @api.multi
    def _get_statement_date_step(self):
        self.ensure_one()
        if self.import_mode == 'daily':
            return relativedelta(
                days=1,
            )
        elif self.import_mode == 'weekly':
            return relativedelta(
                weeks=1,
                weekday=MO,
            )
        elif self.import_mode == 'monthly':
            return relativedelta(
                months=1,
                day=1,
            )

    @api.multi
    def _get_statement_date(self, date_since, date_until):
        self.ensure_one()
        # NOTE: Statement date is treated by Odoo as start of period. Details
        #  - addons/account/models/account_journal_dashboard.py
        #  - def get_line_graph_datas()
        return date_since

    @api.multi
    def _get_statement_name(self, journal, date_since, date_until):
        self.ensure_one()
        return journal.sequence_id.with_context(
            ir_sequence_date=self._get_statement_date(date_since, date_until)
        ).next_by_id()
