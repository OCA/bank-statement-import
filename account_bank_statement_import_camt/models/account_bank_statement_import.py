# -*- coding: utf-8 -*-
# Copyright 2013-2015 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
"""Add process_camt method to account.bank.statement.import."""

import logging
from openerp import api, models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    """Add process_camt method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    @api.model
    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        parser = self.env['account.bank.statement.import.camt.parser']
        try:
            _logger.debug("Try parsing with camt.")
            return parser.parse(data_file)
        except ValueError:
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.", exc_info=True)
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

    @api.model
    def _complete_statement(self, stmt_vals, journal_id, account_number):
        journal = journal_id and self.env['account.journal'].browse(journal_id)
        camt_import_batch = journal and journal.camt_import_batch

        # aggregate batch transactions
        agg_transactions = []
        batch_transactions = {}
        for transaction in stmt_vals.get('transactions', []):
            batch = transaction.pop('batch', None)
            if camt_import_batch:
                if not batch:
                    agg_transactions.append(transaction)
                    continue
                else:
                    if batch not in batch_transactions:
                        transaction.pop('partner_name', None)
                        transaction.pop('account_number', None)
                        transaction['ref'] = batch
                        transaction['name'] = batch
                        agg_transactions.append(transaction)
                        batch_transactions[batch] = transaction
                    else:
                        batch_transactions[batch]['amount'] += \
                            transaction['amount']
        if camt_import_batch and batch_transactions:
            stmt_vals['transactions'] = agg_transactions
            _logger.debug(
                "%d CAMT batch transactions aggregated.",
                (len(batch_transactions),)
            )
        return super(AccountBankStatementImport, self)._complete_statement(
            stmt_vals, journal_id, account_number)
