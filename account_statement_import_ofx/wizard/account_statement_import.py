import io
import logging

from odoo import _, api, models
from odoo.exceptions import UserError
from odoo.tools import plaintext2html

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser
except ImportError:
    _logger.debug("ofxparse not found.")
    OfxParser = None


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    @api.model
    def _check_ofx(self, data_file):
        if not OfxParser:
            return False
        try:
            ofx = OfxParser.parse(io.BytesIO(data_file))
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

        # payment_ref (Label): use payee name only for clean
        # reconciliation matching. Fall back to memo or type
        # if payee is missing (some banks omit NAME).
        payment_ref = transaction.payee or ""
        if not payment_ref and transaction.memo:
            payment_ref = transaction.memo
        elif not payment_ref:
            payment_ref = transaction.type or "/"

        # narration (Note): memo and checknum kept separate from
        # payment_ref so reconciliation models can match on the
        # Note field independently of the Label field.
        narration_parts = []
        if transaction.checknum:
            narration_parts.append(transaction.checknum)
        if transaction.memo:
            narration_parts.append(transaction.memo)
        narration = " ".join(narration_parts)

        vals = {
            "date": transaction.date,
            "payment_ref": payment_ref,
            "amount": float(transaction.amount),
            "unique_import_id": transaction.id,
            "narration": plaintext2html(narration) if narration else False,
            "transaction_type": transaction.type or False,
        }
        if transaction.checknum:
            vals["ref"] = transaction.checknum
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
