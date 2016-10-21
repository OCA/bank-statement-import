# -*- coding: utf-8 -*-
# © 2015-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
"""Provide common base for bank statement import tests."""
import logging

from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


_logger = logging.getLogger(__name__)


class TestStatementFile(TransactionCase):
    """Check wether statements with transactions correctly imported.

    No actual tests are done in this class, implementations are in
    subclasses in actual import modules.
    """
    def create_fiscalyear(self, year):
        """Check wether fiscal year exists. If not create with periods.

        The example files contain dates from the year they were created. Not
        all demo / test databases created in later years will contain the
        fiscal years assumed by the test data. This method allows to
        automatically create the needed data.

        This method assumes fiscal years run from 1st of january to 31
        of december, also for fiscal years that might already exist in
        the database.
        """
        fiscalyear_model = self.env['account.fiscalyear']
        date_start_iso = '%s-01-01' % str(year)
        date_stop_iso = '%s-12-31' % str(year)
        existing_year = fiscalyear_model.search([
            ('date_start', '=', date_start_iso),
            ('company_id', '=', self.env.user.company_id.id),
        ])
        if existing_year:
            return  # Nothing todo
        new_year = fiscalyear_model.create({
            'name': 'Fiscal Year %s' % str(year),
            'code': 'FY%s' % str(year),
            'state': 'draft',
            'company_id': self.env.user.company_id.id,
            'date_start': date_start_iso,
            'date_stop': date_stop_iso,
        })
        new_year.create_period()

    def _test_transaction(
            self, statement_obj, remote_account=False,
            transferred_amount=False, value_date=False, ref=False):
        """Check wether transaction with attributes passed was created.

        Actually this method also tests wether automatic creation of
        partner bank accounts is working.
        """
        transaction_model = self.env['account.bank.statement.line']
        partner_bank_model = self.env['res.partner.bank']
        domain = [('statement_id', '=', statement_obj.id)]
        if remote_account:
            bids = partner_bank_model.search(
                [('acc_number', '=', remote_account)])
            self.assertTrue(
                bids,
                'Bank-account %s not found after parse.' % remote_account
            )
            domain.append(('bank_account_id', '=', bids[0].id))
        if transferred_amount:
            domain.append(('amount', '=', transferred_amount))
        if value_date:
            domain.append(('date', '=', value_date))
        if ref:
            # Relax test for ref, because other modules might add info:
            domain.append(('ref', 'like', ref))
        ids = transaction_model.search(domain)
        if not ids:
            # We will get assertion error, but to solve we need to see
            # what transactions have been added:
            self.cr.execute(
                "SELECT statement_id, name, date, amount, ref, bank_account_id"
                " FROM account_bank_statement_line"
                " WHERE statement_id=%s", (statement_obj.id, ))
            _logger.error(
                "No transaction with domain %s found in %s" %
                (str(domain), str(self.cr.fetchall())))
        self.assertTrue(
            ids,
            'Transaction %s not found after parse.' % str(domain)
        )

    def _test_statement_import(
            self, module_name, file_name, statement_name, local_account=False,
            start_balance=False, end_balance=False, transactions=None):
        """Test correct creation of single statement."""
        import_model = self.env['account.bank.statement.import']
        partner_bank_model = self.env['res.partner.bank']
        statement_model = self.env['account.bank.statement']
        statement_path = get_module_resource(
            module_name,
            'test_files',
            file_name
        )
        statement_file = open(
            statement_path, 'rb').read().encode('base64')
        bank_statement_id = import_model.create(
            dict(
                data_file=statement_file,
                filename=file_name,
            )
        )
        bank_statement_id.import_file()
        # Check wether bank account has been created:
        if local_account:
            bids = partner_bank_model.search(
                [('acc_number', '=', local_account)])
            self.assertTrue(
                bids,
                'Bank account %s not created from statement' % local_account
            )
        # No strict check on name, because extra modules exists that change
        # the names used for statements (e.g. journal sequence):
        ids = statement_model.search([('name', '=', statement_name)])
        if not ids:
            _logger.info(
                'Statement %s not found after parse.' % statement_name
            )
            # Now use SQL to find latest statement added and retrieve that:
            self.env.cr.execute(
                "SELECT id from account_bank_statement"
                " ORDER BY id DESC"
                " LIMIT 1"
            )
            created_id = self.env.cr.fetchone()[0]
            ids = statement_model.browse(created_id)
            _logger.info(
                'Statement created has name %s.' % ids[0].name
            )
        statement_obj = ids[0]
        if start_balance:
            self.assertTrue(
                abs(statement_obj.balance_start - start_balance) < 0.00001,
                'Start balance %f not equal to expected %f' %
                (statement_obj.balance_start, start_balance)
            )
        if end_balance:
            self.assertTrue(
                abs(statement_obj.balance_end_real - end_balance) < 0.00001,
                'End balance %f not equal to expected %f' %
                (statement_obj.balance_end_real, end_balance)
            )
        # Maybe we need to test transactions?
        if transactions:
            for transaction in transactions:
                self._test_transaction(statement_obj, **transaction)
