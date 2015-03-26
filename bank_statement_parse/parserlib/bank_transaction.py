# -*- encoding: utf-8 -*-
"""Define BankTransaction class to help in importing bank transactions."""
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
from openerp.tools.translate import _


class BankTransaction(object):
    """
    A BankTransaction is a real life copy of a bank transfer. Mapping to
    OpenERP moves and linking to invoices and the like is done afterwards.
    """
    # Lock attributes to enable parsers to trigger non-conformity faults
    __slots__ = [
        'id',  # Message id
        'statement_id',  # The bank statement this message was reported on
        'transfer_type',  # Action type that initiated this message
        'reference',  # A reference to this message for communication
        'local_account',  # The account this message was meant for
        'local_currency',  # The currency used for the transferred amount
        'execution_date',  # The posted date of the action
        'value_date',  # The value date of the action
        'remote_account',  # The account of the other party
        'remote_currency',  # The currency used by the other party
        'exchange_rate',
        # The exchange rate used for conversion of local_currency and
        # remote_currency
        'transferred_amount',
        # The actual amount transferred -
        #   negative means sent, positive means received
        # Most banks use the local_currency to express this amount, but there
        # may be exceptions I'm unaware of.
        'message',
        # A direct message from the initiating party to the receiving party
        #   A lot of banks abuse this to stuff all kinds of structured
        #   information in this message. It is the task of the parser to split
        #   this up into the appropriate attributes.
        'remote_owner',  # The name of the other party
        'remote_owner_address',
        # The other parties address lines - the only attribute that is a list
        'remote_owner_city',  # The other parties city name
        'remote_owner_postalcode',  # The other parties zip code belonging
        'remote_owner_country_code',  # The other parties ISO country code
        'remote_bank_bic',  # The bic belonging to other party's bank

        # The following attributes are for allowing banks to communicate about
        # specific transactions. The transferred_amount must include these
        # costs.
        # Please make sure that the costs are signed for the right direction.
        'provision_costs',
        'provision_costs_currency',
        'provision_costs_description',
        # An error message for interaction with the user
        # Only used when mem_transaction.valid returns False.
        'error_message',
        # Storno attribute. When True, make the cancelled debit eligible for
        # a next direct debit run
        'storno_retry',
        # The full extend of data from which the transaction has been parsed
        'data',
    ]

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

    BANK_COSTS = 'BC'
    BANK_TERMINAL = 'BT'
    CHECK = 'CK'
    DIRECT_DEBIT = 'DD'
    ORDER = 'DO'
    PAYMENT_BATCH = 'PB'
    PAYMENT_TERMINAL = 'PT'
    PERIODIC_ORDER = 'PO'
    STORNO = 'ST'

    types = [
        BANK_COSTS, BANK_TERMINAL, CHECK, DIRECT_DEBIT, ORDER,
        PAYMENT_BATCH, PAYMENT_TERMINAL, PERIODIC_ORDER, STORNO,
    ]

    def __init__(self):
        """
        Initialize values
        """
        for attr in self.__slots__:
            setattr(self, attr, '')
        self.remote_owner_address = []
        # (re-)initializations to satisfy pylint
        self.transfer_type = ''
        self.execution_date = ''
        self.remote_account = ''
        self.transferred_amount = ''

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
