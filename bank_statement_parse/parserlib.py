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

# transfer_type's to be used by the business logic.
# Depending on the type your parser gives a transaction, different
# behavior can be triggered in the business logic.
#
#   BANK_COSTS          Automated credited costs by the bank.
#                       Used to generate an automated invoice from the bank
#                       Will be excluded from matching.
#   BANK_TERMINAL       A cash withdrawal from a bank terminal.
#                       Will be excluded from matching.
#   CHECK               A delayed payment. Can be used to trigger extra
#                       moves from temporary accounts. (Money away).
#   DIRECT_DEBIT        Speaks for itself. When outgoing (credit) and
#                       matched, can signal the matched invoice triaged.
#                       Will be selected for matching.
#   ORDER               Order to the bank. Can work both ways.
#                       Will be selected for matching.
#   PAYMENT_BATCH       A payment batch. Can work in both directions.
#                       Incoming payment batch transactions can't be
#                       matched with payments, outgoing can.
#                       Will be selected for matching.
#   PAYMENT_TERMINAL    A payment with debit/credit card in a (web)shop
#                       Invoice numbers and other hard criteria are most
#                       likely missing.
#                       Will be selected for matching
#   PERIODIC_ORDER      An automated payment by the bank on your behalf.
#                       Always outgoing.
#                       Will be selected for matching.
#   STORNO              A failed or reversed attempt at direct debit.
#                       Either due to an action on the payer's side
#                       or a failure observed by the bank (lack of
#                       credit for instance)
#
#   Perhaps more will follow.
#
# When writing parsers, map other types with similar meaning to these to
# prevent cluttering the API. For example: the Dutch ING Bank has a
# transfer type Post Office, meaning a cash withdrawal from one of their
# agencies. This can be mapped to BANK_TERMINAL without losing any
# significance for OpenERP.

# Banks use a wild variety of codes to indicate the kind of action, that
# resulted in a transaction. On parsing these will have to be translated
# to one of the following standard valuues. In the comment the value used
# in previous versions of the banking modules.
TRANSFER_TYPES = [
    'bank_costs',  # BC
    'bank_terminal',  # BT
    'check',  # CK
    'direct_debit',  # DD
    'order',  # DO
    'payment_batch',  # PB
    'payment_terminal',  # PT
    'periodic_order',  # PO
    'storno',  # ST
]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
