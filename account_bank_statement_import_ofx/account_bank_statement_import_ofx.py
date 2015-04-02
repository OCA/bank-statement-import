# -*- coding: utf-8 -*-

import logging
import StringIO

from openerp import api, models
from openerp.tools.translate import _
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)

try:
    from ofxparse import OfxParser as ofxparser
except ImportError:
    _logger.warn("ofxparse not found, OFX parsing disabled.")
    ofxparser = None


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _check_ofx(self, data_file):
        if ofxparser is None:
            return False
        try:
            ofx = ofxparser.parse(StringIO.StringIO(data_file))
        except:
            return False
        return ofx

    @api.model
    def _parse_file(self, data_file):
        ofx = self._check_ofx(data_file)
        if not ofx:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        transactions = []
        total_amt = 0.00
        try:
            for transaction in ofx.account.statement.transactions:
                # Since ofxparse doesn't provide account numbers, we'll have
                # to find res.partner and res.partner.bank here
                # (normal behavious is to provide 'account_number', which the
                # generic module uses to find partner/bank)
                bank_account_id = partner_id = False
                banks = self.env['res.partner.bank'].search(
                    [('owner_name', '=', transaction.payee)], limit=1)
                if banks:
                    bank_account = banks[0]
                    bank_account_id = bank_account.id
                    partner_id = bank_account.partner_id.id
                vals_line = {
                    'date': transaction.date,
                    'name': transaction.payee + (
                        transaction.memo and ': ' + transaction.memo or ''),
                    'ref': transaction.id,
                    'amount': transaction.amount,
                    'unique_import_id': transaction.id,
                    'bank_account_id': bank_account_id,
                    'partner_id': partner_id,
                }
                total_amt += float(transaction.amount)
                transactions.append(vals_line)
        except Exception, e:
            raise Warning(_("The following problem occurred during import. "
                            "The file might not be valid.\n\n %s" % e.message))

        return [{
            'currency_code': ofx.account.statement.currency,
            'account_number': ofx.account.number,
            'name': ofx.account.routing_number,
            'transactions': transactions,
            'balance_start': ofx.account.statement.balance,
            'balance_end_real':
                float(ofx.account.statement.balance) + total_amt,
        }]
