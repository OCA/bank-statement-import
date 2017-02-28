# coding: utf-8
# © 2017 Opener BV (<https://opener.amsterdam>)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from io import BytesIO
from openpyxl import load_workbook
from zipfile import BadZipfile

from openerp import models, api
from openerp.exceptions import Warning as UserError
from openerp.tools.misc import DEFAULT_SERVER_DATE_FORMAT as DATEFMT
from openerp.tools.translate import _
from openerp.addons.account_bank_statement_import.parserlib import (
    BankStatement)


class Import(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse an Adyen xlsx file and map merchant account strings
        to journals. """
        try:
            statements = self.import_adyen_xlsx(data_file)
        except ValueError:
            return super(Import, self)._parse_file(data_file)

        for statement in statements:
            merchant_id = statement['account_number']
            journal = self.env['account.journal'].search([
                ('adyen_merchant_account', '=', merchant_id)], limit=1)
            if journal:
                statement['adyen_journal_id'] = journal.id
            else:
                raise UserError(
                    _('Please create a journal with merchant account "%s"') %
                    merchant_id)
            statement['account_number'] = False
        return statements

    @api.model
    def _import_statement(self, stmt_vals):
        """ Propagate found journal to context, fromwhere it is picked up
        in _get_journal """
        journal_id = stmt_vals.pop('adyen_journal_id', None)
        if journal_id:
            self = self.with_context(journal_id=journal_id)
        return super(Import, self)._import_statement(stmt_vals)

    @api.model
    def balance(self, row):
        return -(row[15] or 0) + sum(
            row[i] if row[i] else 0.0
            for i in (16, 17, 18, 19, 20))

    @api.model
    def import_adyen_transaction(self, statement, row):
        transaction = statement.create_transaction()
        transaction.value_date = row[6].strftime(DATEFMT)
        transaction.transferred_amount = self.balance(row)
        transaction.note = (
            '%s %s %s %s' % (row[2], row[3], row[4], row[21]))
        transaction.message = "%s" % (row[3] or row[4] or row[9])
        return transaction

    @api.model
    def import_adyen_xlsx(self, data_file):
        statements = []
        statement = None
        headers = False
        fees = 0.0
        balance = 0.0
        payout = 0.0

        with BytesIO() as buf:
            buf.write(data_file)
            try:
                sheet = load_workbook(buf)._sheets[0]
            except BadZipfile as e:
                raise ValueError(e)
            for row in sheet.rows:
                row = [cell.value for cell in row]
                if len(row) != 31:
                    raise ValueError(
                        'Not an Adyen statement. Unexpected row length %s '
                        'instead of 31' % len(row))
                if not row[1]:
                    continue
                if not headers:
                    if row[1] != 'Company Account':
                        raise ValueError(
                            'Not an Adyen statement. Unexpected header "%s" '
                            'instead of "Company Account"', row[1])
                    headers = True
                    continue
                if not statement:
                    statement = BankStatement()
                    statements.append(statement)
                    statement.statement_id = '%s %s/%s' % (
                        row[2], row[6].strftime('%Y'), int(row[23]))
                    statement.local_currency = row[14]
                    statement.local_account = row[2]
                date = row[6].strftime(DATEFMT)
                if not statement.date or statement.date > date:
                    statement.date = date

                row[8] = row[8].strip()
                if row[8] == 'MerchantPayout':
                    payout -= self.balance(row)
                else:
                    balance += self.balance(row)
                self.import_adyen_transaction(statement, row)
                fees += sum(
                    row[i] if row[i] else 0.0
                    for i in (17, 18, 19, 20))

        if not headers:
            raise ValueError(
                'Not an Adyen statement. Did not encounter header row.')

        if fees:
            transaction = statement.create_transaction()
            transaction.value_date = max(
                t.value_date for t in statement['transactions'])
            transaction.transferred_amount = -fees
            balance -= fees
            transaction.message = 'Commision, markup etc. batch %s' % (
                int(row[23]))

        if statement['transactions'] and not payout:
            raise UserError(
                _('No payout detected in Adyen statement.'))
        if self.env.user.company_id.currency_id.compare_amounts(
                balance, payout) != 0:
            raise UserError(
                _('Parse error. Balance %s not equal to merchant '
                  'payout %s') % (balance, payout))

        return statements
