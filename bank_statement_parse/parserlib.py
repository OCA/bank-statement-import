# -*- encoding: utf-8 -*-
"""Classes and definitions used in parsing bank statements."""
##############################################################################
#
#  Copyright (C) 2015 Therp BV - http://therp.nl.
#  All Rights Reserved
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


def convert_transaction(transaction):
    """Convert transaction object to values for create."""
    vals_line = {
        'date': transaction.value_date,
        'name': (
            transaction.message or transaction.eref or
            transaction.remote_owner or ''),  # name is required
        'ref': transaction.eref,
        'amount': transaction.transferred_amount,
        'partner_name': transaction.remote_owner,
        'account_number': transaction.remote_account,
        'unique_import_id': transaction.transaction_id,
    }
    return vals_line


def convert_statements(statements):
    """Convert statement object to values for create."""
    vals_statements = []
    for statement in statements:
        # Set statement_data
        vals_statement = {
            'currency_code': statement.local_currency,
            'account_number': statement.local_account,
            'name': statement.statement_id,
            'date': statement.date.strftime('%Y-%m-%d'),
            'balance_start': statement.start_balance,
            'balance_end_real': statement.end_balance,
            'balance_end': statement.end_balance,
            'state': 'draft',
        }
        statement_transactions = []
        subno = 0
        for transaction in statement.transactions:
            subno += 1
            if not transaction.transaction_id:
                transaction.transaction_id = (
                    statement.statement_id + str(subno).zfill(4))
            statement_transactions.append(convert_transaction(transaction))
        vals_statement['transactions'] = statement_transactions
        vals_statements.append(vals_statement)
    return vals_statements


class BankStatement(object):
    """A bank statement groups data about several bank transactions."""

    def __init__(self):
        self.statement_id = ''
        self.local_account = ''
        self.local_currency = ''
        self.start_balance = 0.0
        self.end_balance = 0.0
        self.date = ''
        self.transactions = []


class BankTransaction(object):
    """Single transaction that is part of a bank statement."""

    def __init__(self):
        """Define and initialize attributes.

        Does not include attributes that belong to statement.
        """
        self.transaction_id = False  # Message id
        self.transfer_type = False  # Action type that initiated this message
        self.eref = False  # end to end reference for transactions
        self.execution_date = False  # The posted date of the action
        self.value_date = False  # The value date of the action
        self.remote_account = False  # The account of the other party
        self.remote_currency = False  # The currency used by the other party
        self.exchange_rate = 0.0
        # The exchange rate used for conversion of local_currency and
        # remote_currency
        self.transferred_amount = 0.0  # actual amount transferred
        self.message = False  # message from the remote party
        self.remote_owner = False  # name of the other party
        self.remote_owner_address = []  # other parties address lines
        self.remote_owner_city = False  # other parties city name
        self.remote_owner_postalcode = False  # other parties zip code
        self.remote_owner_country_code = False  # other parties country code
        self.remote_bank_bic = False  # bic of other party's bank
        self.provision_costs = False  # costs charged by bank for transaction
        self.provision_costs_currency = False
        self.provision_costs_description = False
        self.error_message = False  # error message for interaction with user
        self.storno_retry = False
        # If True, make cancelled debit eligible for a next direct debit run
        self.data = ''  # Raw data from which the transaction has been parsed

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
