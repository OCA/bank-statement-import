import io
import logging
import re

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

    @api.model
    def _decode_ofx_file(self, data_file):
        """Decode raw OFX bytes to text, working around mislabeled charsets.

        Some banks emit OFX whose SGML header declares one charset (e.g.
        ``CHARSET:1252``) while the body is actually encoded differently
        (UTF-8 is common). ofxparse trusts that header and decodes with a
        strict cp1252 codec, which raises ``UnicodeDecodeError`` on bytes
        undefined in cp1252 (e.g. ``0x81``); the import then fails with a
        misleading "file format not supported" message.

        We decode the bytes ourselves: UTF-8 first (it is self-validating,
        so it rarely matches non-UTF-8 data by accident), then the charset
        declared in the header, and finally latin-1, which maps every byte
        value and therefore never raises. Returns the decoded text or None.
        """
        declared = None
        for line in data_file[:1024].splitlines():
            if line.upper().startswith(b"CHARSET:"):
                value = line.split(b":", 1)[1].strip().upper()
                declared = {b"1252": "cp1252", b"8859-1": "latin-1"}.get(value)
                break

        encodings = ["utf-8-sig"]
        if declared and declared not in encodings:
            encodings.append(declared)
        if "latin-1" not in encodings:
            encodings.append("latin-1")

        for encoding in encodings:
            try:
                return data_file.decode(encoding)
            except UnicodeDecodeError:
                continue
        return None

    @api.model
    def _check_ofx(self, data_file):
        if not OfxParser:
            return False
        text = self._decode_ofx_file(data_file)
        if text is None:
            return False
        # Re-encode to UTF-8 and normalize the SGML ENCODING header so that
        # ofxparse decodes the body consistently, regardless of the (possibly
        # wrong) charset originally declared in the file. Passing bytes (not a
        # text stream) avoids ofxparse re-decoding the body via its own logic.
        text = re.sub(r"(?im)^ENCODING:.*$", "ENCODING:UTF-8", text, count=1)
        try:
            return OfxParser.parse(io.BytesIO(text.encode("utf-8")))
        except Exception as e:
            _logger.debug(e)
            return False

    @api.model
    def _prepare_ofx_transaction_line(self, transaction):
        # Since ofxparse doesn't provide account numbers,
        # we cannot provide the key 'bank_account_id',
        # nor the key 'account_number'
        # If you read odoo10/addons/account_bank_statement_import/
        # account_bank_statement_import.py, it's the only 2 keys
        # we can provide to match a partner.
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
