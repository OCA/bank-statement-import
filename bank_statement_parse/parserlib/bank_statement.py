# -*- encoding: utf-8 -*-
"""Define BankStatement class to help in importing bank statements."""
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


class BankStatement(object):
    """
    A BankStatement is a real life projection of a bank statement paper
    containing a report of one or more transactions done.
    """
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
        self.id = ''
        self.local_account = ''
        self.local_currency = ''
        self.start_balance = 0.0
        self.end_balance = 0.0
        self.date = ''
        self.transactions = []

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
