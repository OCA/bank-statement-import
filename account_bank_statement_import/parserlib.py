# -*- encoding: utf-8 -*-
"""Classes and definitions used in parsing bank statements."""
##############################################################################
#
#  Copyright (C) 2015 Therp BV <http://therp.nl>.
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


class BankTransaction(dict):
    """Single transaction that is part of a bank statement."""

    @property
    def value_date(self):
        """property getter"""
        return self['date']

    @value_date.setter
    def value_date(self, value_date):
        """property setter"""
        self['date'] = value_date

    @property
    def name(self):
        """property getter"""
        return self['name']

    @name.setter
    def name(self, name):
        """property setter"""
        self['name'] = name

    @property
    def transferred_amount(self):
        """property getter"""
        return self['amount']

    @transferred_amount.setter
    def transferred_amount(self, transferred_amount):
        """property setter"""
        self['amount'] = transferred_amount

    @property
    def eref(self):
        """property getter"""
        return self['ref']

    @eref.setter
    def eref(self, eref):
        """property setter"""
        self['ref'] = eref
        if not self.message:
            self.name = eref

    @property
    def message(self):
        """property getter"""
        return self._message

    @message.setter
    def message(self, message):
        """property setter"""
        self._message = message
        self.name = message

    @property
    def remote_owner(self):
        """property getter"""
        return self['partner_name']

    @remote_owner.setter
    def remote_owner(self, remote_owner):
        """property setter"""
        self['partner_name'] = remote_owner
        if not (self.message or self.eref):
            self.name = remote_owner

    @property
    def remote_account(self):
        """property getter"""
        return self['account_number']

    @remote_account.setter
    def remote_account(self, remote_account):
        """property setter"""
        self['account_number'] = remote_account

    @property
    def note(self):
        return self['note']

    @note.setter
    def note(self, note):
        self['note'] = note

    def __init__(self):
        """Define and initialize attributes.

        Not all attributes are already used in the actual import.
        """
        super(BankTransaction, self).__init__()
        self.transfer_type = False  # Action type that initiated this message
        self.execution_date = False  # The posted date of the action
        self.value_date = False  # The value date of the action
        self.remote_account = False  # The account of the other party
        self.remote_currency = False  # The currency used by the other party
        self.exchange_rate = 0.0
        # The exchange rate used for conversion of local_currency and
        # remote_currency
        self.transferred_amount = 0.0  # actual amount transferred
        self.name = ''
        self._message = False  # message from the remote party
        self.eref = False  # end to end reference for transactions
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


class BankStatement(dict):
    """A bank statement groups data about several bank transactions."""

    @property
    def statement_id(self):
        """property getter"""
        return self['name']

    def _set_transaction_ids(self):
        """Set transaction ids to statement_id with sequence-number."""
        subno = 0
        for transaction in self['transactions']:
            subno += 1
            transaction['unique_import_id'] = (
                self.statement_id + str(subno).zfill(4))

    @statement_id.setter
    def statement_id(self, statement_id):
        """property setter"""
        self['name'] = statement_id
        self._set_transaction_ids()

    @property
    def local_account(self):
        """property getter"""
        return self['account_number']

    @local_account.setter
    def local_account(self, local_account):
        """property setter"""
        self['account_number'] = local_account

    @property
    def local_currency(self):
        """property getter"""
        return self['currency_code']

    @local_currency.setter
    def local_currency(self, local_currency):
        """property setter"""
        self['currency_code'] = local_currency

    @property
    def start_balance(self):
        """property getter"""
        return self['balance_start']

    @start_balance.setter
    def start_balance(self, start_balance):
        """property setter"""
        self['balance_start'] = start_balance

    @property
    def end_balance(self):
        """property getter"""
        return self['balance_end']

    @end_balance.setter
    def end_balance(self, end_balance):
        """property setter"""
        self['balance_end'] = end_balance
        self['balance_end_real'] = end_balance

    @property
    def date(self):
        """property getter"""
        return self['date']

    @date.setter
    def date(self, date):
        """property setter"""
        self['date'] = date

    def create_transaction(self):
        """Create and append transaction.

        This should only be called after statement_id has been set, because
        statement_id will become part of the unique transaction_id.
        """
        transaction = BankTransaction()
        self['transactions'].append(transaction)
        # Fill default id, but might be overruled
        transaction['unique_import_id'] = (
            self.statement_id + str(len(self['transactions'])).zfill(4))
        return transaction

    def __init__(self):
        super(BankStatement, self).__init__()
        self['transactions'] = []
        self.statement_id = ''
        self.local_account = ''
        self.local_currency = ''
        self.date = ''
        self.start_balance = 0.0
        self.end_balance = 0.0
