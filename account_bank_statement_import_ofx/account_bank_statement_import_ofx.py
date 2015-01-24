# -*- coding: utf-8 -*-
# noqa: This is a backport from Odoo. OCA has no control over style here.
# flake8: noqa

import logging
import base64
import os

from openerp.osv import osv
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)

from openerp.addons.account_bank_statement_import import account_bank_statement_import as ibs
ibs.add_file_type(('ofx', 'OFX'))

try:
    from ofxparse import OfxParser as ofxparser
except ImportError:
    _logger.warning("OFX parser unavailable because the `ofxparse` Python library cannot be found."
                    "It can be downloaded and installed from `https://pypi.python.org/pypi/ofxparse`.")
    ofxparser = None

class account_bank_statement_import(osv.Model):  # Not transient!
    _inherit = 'account.bank.statement.import'

    def process_ofx(self, cr, uid, data_file, context=None):
        """ Import a file in the .OFX format"""
        if ofxparser is None:
            raise osv.except_osv(
                _("Error"),
                _("OFX parser unavailable because the `ofxparse` Python library cannot be found."
                  "It can be downloaded and installed from `https://pypi.python.org/pypi/ofxparse`.")
            )
        try:
            tempfile = open("temp.ofx", "w+")
            tempfile.write(base64.decodestring(data_file))
            tempfile.read()
            pathname = os.path.dirname('temp.ofx')
            path = os.path.join(os.path.abspath(pathname), 'temp.ofx')
            ofx = ofxparser.parse(file(path))
        except:
            raise osv.except_osv(_('Import Error!'), _('Please check OFX file format is proper or not.'))
        line_ids = []
        total_amt = 0.00
        try:
            for transaction in ofx.account.statement.transactions:
                bank_account_id, partner_id = self._detect_partner(cr, uid, transaction.payee, identifying_field='owner_name', context=context)
                vals_line = {
                    'date': transaction.date,
                    'name': transaction.payee + ': ' + transaction.memo,
                    'ref': transaction.id,
                    'amount': transaction.amount,
                    'partner_id': partner_id,
                    'bank_account_id': bank_account_id,
                }
                total_amt += float(transaction.amount)
                line_ids.append((0, 0, vals_line))
        except Exception, e:
            raise osv.except_osv(_('Error!'), _("Following problem has been occurred while importing your file, Please verify the file is proper or not.\n\n %s" % e.message))
        st_start_date = ofx.account.statement.start_date or False
        st_end_date = ofx.account.statement.end_date or False
        statement_date = st_end_date or st_start_date or False
        vals_bank_statement = {
            'date': statement_date,
            'acc_number': ofx.account.number,
            'name': ofx.account.routing_number,
            'balance_start': ofx.account.statement.balance,
            'balance_end_real': float(ofx.account.statement.balance) + total_amt,
        }
        vals_bank_statement.update({'line_ids': line_ids})
        os.remove(path)
        return [vals_bank_statement]

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
