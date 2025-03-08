import io
import logging

from typing import Literal

from ofxparse.ofxparse import Ofx

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser
except ImportError:
    _logger.debug("ofxparse not found.")
    OfxParser = None


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _check_ofx(self, data_file:bytes) -> Ofx | Literal[False]:
        if not OfxParser:
            return False

        # Previous implementation tried to parse the ofx file, but this had the effect of suppressing helpful messages about the ofx file. Here we just just for the tag.
        try:
            # Convert data_file to string and check for "<ofx>" case insensitive
            data_str = data_file.decode('utf-8', errors='ignore')
            if "<ofx>".lower() not in data_str.lower():
                return False
            
            ofx = OfxParser.parse(io.BytesIO(data_file))
            return ofx
        except Exception as e:
            _logger.debug(e)
            raise UserError(
                _(
                    "The following problem occurred during import. "
                    "The file might not be valid.\n\n %s"
                )
                % str(e)
            ) from e   
    @api.model
    def _prepare_ofx_transaction_line(self, transaction):
        # Since ofxparse doesn't provide account numbers,
        # we cannot provide the key 'account_number'
        # If you read the code of the module account_statement_import_base
        # it's the only key we can provide to match a partner.
        payment_ref = transaction.payee
        if transaction.checknum:
            payment_ref += " " + transaction.checknum
        if transaction.memo:
            payment_ref += " : " + transaction.memo
        vals = {
            "date": transaction.date,
            "payment_ref": payment_ref,
            "amount": float(transaction.amount),
            "unique_import_id": transaction.id,
        }
        return vals

    def _parse_file(self, data_file):
        ofx = self._check_ofx(data_file)
        if not ofx:
            return super()._parse_file(data_file)

        result = []
        try:
            for account in ofx.accounts:
                transactions = []
                total_amt = 0.00

                if not account.statement.transactions:
                    continue

                for transaction in account.statement.transactions:
                    vals = self._prepare_ofx_transaction_line(transaction)
                    if vals:
                        transactions.append(vals)
                        total_amt += vals["amount"]
                balance = float(account.statement.balance)
                vals_bank_statement = {
                    "name": account.number,
                    "transactions": transactions,
                    "balance_start": balance - total_amt,
                    "balance_end_real": balance,
                }
                result.append(
                    (account.statement.currency, account.number, [vals_bank_statement])
                )
        except Exception as e:
            raise UserError(
                _(
                    "The following problem occurred during import. "
                    "The file might not be valid.\n\n %s"
                )
                % str(e)
            ) from e
        return result
