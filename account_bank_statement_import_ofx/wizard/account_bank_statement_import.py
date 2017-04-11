# -*- coding: utf-8 -*-

import logging
import StringIO

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser
except ImportError:
    _logger.debug("ofxparse not found.")
    OfxParser = None


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _check_ofx(self, data_file):
        if not OfxParser:
            return False
        try:
            ofx = OfxParser.parse(StringIO.StringIO(data_file))
        except Exception as e:
            _logger.debug(e)
            return False
        return ofx

    @api.model
    def _prepare_ofx_transaction_line(self, transaction):
        # Since ofxparse doesn't provide account numbers,
        # we cannot provide the key 'bank_account_id',
        # nor the key 'account_number'
        # If you read odoo10/addons/account_bank_statement_import/
        # account_bank_statement_import.py, it's the only 2 keys
        # we can provide to match a partner.
        vals = {
            'date': transaction.date,
            'name': transaction.payee + (
                transaction.memo and ': ' + transaction.memo or ''),
            'ref': transaction.id,
            'amount': float(transaction.amount),
            'unique_import_id': transaction.id,
        }
        return vals

    def _parse_file(self, data_file):
        ofx = self._check_ofx(data_file)
        if not ofx:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        transactions = []
        total_amt = 0.00
        try:
            for transaction in ofx.account.statement.transactions:
                vals = self._prepare_ofx_transaction_line(transaction)
                if vals:
                    transactions.append(vals)
                    total_amt += vals['amount']
        except Exception, e:
            raise UserError(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s") % e.message)

        balance = float(ofx.account.statement.balance)
        vals_bank_statement = {
            'name': ofx.account.number,
            'transactions': transactions,
            'balance_start': balance - total_amt,
            'balance_end_real': balance,
        }
        return ofx.account.statement.currency, ofx.account.number, [
            vals_bank_statement]
