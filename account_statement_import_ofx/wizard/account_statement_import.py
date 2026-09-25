import io
import logging

from odoo import _, api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser, OfxParserException

    OriginalOfxParser = OfxParser

except ImportError:
    _logger.debug("ofxparse not found.")
    OfxParser = None
    OfxParserClass = object


class PatchedOfxParser(OriginalOfxParser):
    """This class monkey-patches the ofxparse library:
    -
    """

    @classmethod
    def parseBalance(
        cls, statement, stmt_ofx, bal_tag_name, bal_attr, bal_date_attr, bal_type_string
    ):  # pylint: disable=W8110
        try:
            super().parseBalance(
                statement,
                stmt_ofx,
                bal_tag_name,
                bal_attr,
                bal_date_attr,
                bal_type_string,
            )
        except OfxParserException:
            _logger.warning(
                f"Empty balance ('ledgerbal/balamt')."
                f" 'statement.{bal_attr}' will be empty."
            )


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    @api.model
    def _check_ofx(self, data_file):
        if not OfxParser:
            return False
        ofx = PatchedOfxParser.parse(io.BytesIO(data_file))
        return ofx

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

                vals_bank_statement = {
                    "name": account.number,
                    "transactions": transactions,
                }
                if hasattr(account.statement, "balance"):
                    balance = account.statement.balance
                    vals_bank_statement.update(
                        {
                            "balance_start": balance - total_amt,
                            "balance_end_real": balance,
                        }
                    )
                else:
                    vals_bank_statement.update(
                        {
                            "balance_start": 0.0,
                            "balance_end_real": 0.0,
                        }
                    )
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
