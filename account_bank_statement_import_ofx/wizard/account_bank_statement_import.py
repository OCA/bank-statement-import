import logging
import io

from odoo import api, models, _
from odoo.exceptions import UserError
from odoo.addons.base_iban.models.res_partner_bank import _map_iban_template
from odoo.addons.base_iban.models.res_partner_bank import validate_iban

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser
except ImportError:
    _logger.debug("ofxparse not found.")
    OfxParser = None


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _check_journal_bank_account(self, journal, account_number):
        res = super(
            AccountBankStatementImport, self
        )._check_journal_bank_account(journal, account_number)
        if not res:
            e_acc_num = journal.bank_account_id.sanitized_acc_number
            e_acc_num = e_acc_num.replace(" ", "")
            validate_iban(e_acc_num)
            country_code = e_acc_num[:2].lower()
            iban_template = _map_iban_template[country_code].replace(
                " ", "")
            e_acc_num = "".join(
                [c for c, t in zip(e_acc_num, iban_template) if t == "C"])
            res = (e_acc_num == account_number)
        return res

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
        except Exception as e:
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
