# -*- encoding: utf-8 -*-
"""Decorator provides 'glue' between pre 8.0 import wizards and 8.0 style."""
##############################################################################
#
#    Copyright (C) 2014 Therp BV - http://therp.nl.
#    All Rights Reserved
#
#    WARNING: This program as such is intended to be used by professional
#    programmers who take the whole responsability of assessing all potential
#    consequences resulting from its eventual inadequacies and bugs
#    End users who are looking for a ready-to-use solution with commercial
#    garantees and support are strongly adviced to contract EduSense BV
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
import base64
from . import convert


def convert_statements(
        model, cr, uid, os_statements, journal_id=False, context=None):
    """Taking lots of code from the former import wizard, convert array
    of BankStatement objects to values that can be used in create of
    bank.statement model, including bank.statement.line tuple."""
    # os_ = old style
    # ns_ = new style
    def convert_transaction(
            model, cr, uid, transaction, subno, context=None):
        """Convert transaction object to values for create."""
        transaction_model = model.pool['account.bank.statement.line']
        partner_vals = {
            'name': transaction.remote_owner,
        }
        bank_vals = {
            'acc_number': transaction.remote_account,
            'owner_name': transaction.remote_owner or False,
            'street': transaction.remote_owner_address or False,
            'city': transaction.remote_owner_city or False,
            'zip': transaction.remote_owner_postalcode or False,
            'country_code': transaction.remote_owner_country_code or False,
            'bank_bic': transaction.remote_bank_bic or False,
        }
        bank_account_id, partner_id = model.detect_partner_and_bank(
            cr, uid, transaction_vals=None, partner_vals=partner_vals,
            bank_vals=bank_vals, context=context
        )
        if not transaction.id:
            transaction.id = str(subno)
        vals_line = {
            'date': transaction.value_date,
            'name': (
                transaction.message or transaction.reference or
                transaction.remote_owner or ''),  # name is required
            'ref': transaction.reference,
            'amount': transaction.transferred_amount,
            'partner_id': partner_id,
            'partner_name': transaction.remote_owner,
            'bank_account_id': bank_account_id,
        }
        # Transfer any additional transaction attributes for which columns
        # have been defined:
        for attr in transaction.__slots__:
            if attr in transaction_model._columns and attr not in vals_line:
                vals_line[attr] = getattr(transaction, attr)
        return vals_line

    ns_statements = []
    for statement in os_statements:
        # Set company_id from journal
        company_id = False
        if journal_id:
            journal_model = model.pool['account.journal']
            journal_obj = journal_model.browse(
                cr, uid, [journal_id], context=context)
            company_id = journal_obj[0].company_id.id
        # Set statement_date
        statement_date = convert.date2str(statement.date)
        # Set period_id from statement_date
        period_id = False
        period_model = model.pool['account.period']
        if statement_date:
            period_ids = period_model.find(
                cr, uid, statement_date, context=context)
            period_id = period_ids and period_ids[0] or False
        ns_statement = dict(
            name=statement.id,
            journal_id=journal_id,
            date=statement_date,
            balance_start=statement.start_balance,
            balance_end_real=statement.end_balance,
            balance_end=statement.end_balance,
            state='draft',
            user_id=uid,
            # banking_id=import_id,
            company_id=company_id,
            period_id=period_id,
        )
        line_ids = []
        subno = 0
        for transaction in statement.transactions:
            subno += 1
            line_ids.append((
                0, 0,
                convert_transaction(
                    model, cr, uid, transaction, subno, context=context),
            ))
        ns_statement['line_ids'] = line_ids
        ns_statements.append(ns_statement)
    return ns_statements


def advanced_parser(old_style_parser):
    """Turn the old style three parameter function and change it automagically
    in a six parameter function expected by the new style import."""
    def wrapper(self, cr, uid, data_file, journal_id=False, context=None):
        """Add extra parameters and functionality to old style parsers."""
        decoded_data = base64.decodestring(data_file)
        os_statements = old_style_parser(self, cr, decoded_data)
        return convert_statements(
            self, cr, uid, os_statements, journal_id=journal_id,
            context=context
        )
    return wrapper

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
