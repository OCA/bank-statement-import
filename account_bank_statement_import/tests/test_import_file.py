# -*- coding: utf-8 -*-
"""Provide common base for bank statement import tests."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    All other contributions are (C) by their respective contributors
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import logging

from openerp.tests.common import TransactionCase
from openerp.modules.module import get_module_resource


_logger = logging.getLogger(__name__)


class TestStatementFile(TransactionCase):
    """Check wether statements with transactions correctly imported.

    No actual tests are done in this class, implementations are in
    subclasses in actual import modules.
    """

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
            domain.append(('ref', '=', ref))
        ids = transaction_model.search(domain)
        if not ids:
            # We will get assertion error, but to solve we need to see
            # what transactions have been added:
            self.cr.execute(
                "select name, date, amount, ref, bank_account_id"
                " from account_bank_statement_line"
                " where statement_id=%d" % statement_obj.id)
            _logger.error(
                "Transaction not found in %s" %
                str(self.cr.fetchall())
            )
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
        # statement name is account number + '-' + date of last 62F line:
        ids = statement_model.search([('name', '=', statement_name)])
        self.assertTrue(
            ids,
            'Statement %s not found after parse.' % statement_name
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
