# -*- encoding: utf-8 -*-
##############################################################################
#
#  Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
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
import re
from openerp.tools.translate import _


class BankStatement(object):
    '''
    A BankStatement is a real life projection of a bank statement paper
    containing a report of one or more transactions done. As these reports can
    contain payments that originate in several accounting periods, period is an
    attribute of mem_bank_transaction, not of BankStatement.
    Also note that the statement_id is copied from the bank statement, and not
    generated from any sequence. This enables us to skip old data in new
    statement files.
    '''
    # Lock attributes to enable parsers to trigger non-conformity faults
    __slots__ = [
        'start_balance',
        'end_balance',
        'date',
        'local_account',
        'local_currency',
        'id',
        'transactions'
    ]

    def __init__(self, *args, **kwargs):
        super(BankStatement, self).__init__(*args, **kwargs)
        self.id = ''
        self.local_account = ''
        self.local_currency = ''
        self.start_balance = 0.0
        self.end_balance = 0.0
        self.date = ''
        self.transactions = []

    def is_valid(self):
        '''
        Final check: ok if calculated end_balance and parsed end_balance are
        identical and perform a heuristic check on the transactions.
        '''
        if any([x for x in self.transactions if not x.is_valid()]):
            return False
        check = float(self.start_balance)
        for transaction in self.transactions:
            check += float(transaction.transferred_amount)
        return abs(check - float(self.end_balance)) < 0.0001
