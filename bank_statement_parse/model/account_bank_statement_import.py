# -*- coding: utf-8 -*-
"""Extend account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    All Rights Reserved
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
from openerp import models
from openerp.tools.translate import _


class AccountBankStatementImport(models.TransientModel):
    """Import Bank Statements File."""
    _inherit = 'account.bank.statement.import'
    _description = __doc__

    def convert_transaction(
            self, cr, uid, transaction, context=None):
        """Convert transaction object to values for create."""
        partner_vals = {
            'name': transaction.remote_owner,
        }
        bank_vals = {
            'acc_number': transaction.remote_account,
            'owner_name': transaction.remote_owner,
            'street': transaction.remote_owner_address,
            'city': transaction.remote_owner_city,
            'zip': transaction.remote_owner_postalcode,
            'country_code': transaction.remote_owner_country_code,
            'bank_bic': transaction.remote_bank_bic,
        }
        bank_account_id, partner_id = self.detect_partner_and_bank(
            cr, uid, transaction_vals=None, partner_vals=partner_vals,
            bank_vals=bank_vals, context=context
        )
        vals_line = {
            'date': transaction.value_date,
            'name': (
                transaction.message or transaction.eref or
                transaction.remote_owner or ''),  # name is required
            'ref': transaction.eref,
            'amount': transaction.transferred_amount,
            'partner_name': transaction.remote_owner,
            'acc_number': transaction.remote_account,
            'partner_id': partner_id,
            'bank_account_id': bank_account_id,
            'unique_import_id': transaction.transaction_id,
        }
        return vals_line

    def convert_statements(
            self, cr, uid, os_statements, context=None):
        """Taking lots of code from the former import wizard, convert array
        of BankStatement objects to values that can be used in create of
        bank.statement model, including bank.statement.line tuple."""
        # os_ = old style
        # ns_ = new style
        ns_statements = []
        for statement in os_statements:
            # Set statement_data
            ns_statement = dict(
                acc_number=statement.local_account,
                name=statement.statement_id,
                date=statement.date.strftime('%Y-%m-%d'),
                balance_start=statement.start_balance,
                balance_end_real=statement.end_balance,
                balance_end=statement.end_balance,
                state='draft',
                user_id=uid,
            )
            ns_transactions = []
            subno = 0
            for transaction in statement.transactions:
                subno += 1
                if not transaction.transaction_id:
                    transaction.transaction_id = (
                        statement.statement_id + str(subno).zfill(4))
                ns_transactions.append(
                    self.convert_transaction(
                        cr, uid, transaction, context=context))
            ns_statement['transactions'] = ns_transactions
            ns_statements.append(ns_statement)
        return (
            # For the moment all statements must have same currency and amount
            ns_statements[0].local_currency,
            ns_statements[0].local_account,
            ns_statements,
        )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
