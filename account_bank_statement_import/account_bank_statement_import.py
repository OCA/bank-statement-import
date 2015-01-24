# -*- coding: utf-8 -*-
# noqa: This is a backport from Odoo. OCA has no control over style here.
# flake8: noqa

from openerp.osv import fields, osv
from openerp.tools.translate import _

import logging
_logger = logging.getLogger(__name__)

_IMPORT_FILE_TYPE = [('none', _('No Import Format Available'))]

def add_file_type(selection_value):
    global _IMPORT_FILE_TYPE
    if _IMPORT_FILE_TYPE[0][0] == 'none':
        _IMPORT_FILE_TYPE = [selection_value]
    else:
        _IMPORT_FILE_TYPE.append(selection_value)

class account_bank_statement_import(osv.Model): # Not transient in backport!

    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    def _get_import_file_type(self, cr, uid, context=None):
        return _IMPORT_FILE_TYPE

    _columns = {
        'data_file': fields.binary('Bank Statement File', required=True, help='Get you bank statements in electronic format from your bank and select them here.'),
        'file_type': fields.selection(_get_import_file_type, 'File Type', required=True),
    }

    def _get_first_file_type(self, cr, uid, context=None):
        return self._get_import_file_type(cr, uid, context=context)[0][0]

    _defaults = {
        'file_type': _get_first_file_type,
    }

    def import_bank_statement(self, cr, uid, bank_statement_vals=False, context=None):
        """ Get a list of values to pass to the create() of account.bank.statement object, and returns a list of ID created using those values"""
        statement_ids = []
        bank_model = self.pool['res.partner.bank']
        period_model = self.pool['account.period']
        for vals in bank_statement_vals:
            # Find journal_id from bank account
            if 'acc_number' not in vals:
                raise osv.except_osv(
                    _('Error'),
                    _('No account number in bank statement')
                )
            acc_number = vals['acc_number']
            ids = bank_model.search(
                cr, uid, [('acc_number', '=', acc_number)], context=context)
            if not ids:
                raise osv.except_osv(
                    _('Error'),
                    _('No account found for %s') % acc_number
                )
            bank_records = bank_model.read(
                cr, uid, ids, ['journal_id', 'company_id'], context=context)
            if not bank_records[0]['journal_id']:
                raise osv.except_osv(
                    _('Error'),
                    _('No journal set for bank-account %s') % acc_number
                )
            del vals['acc_number']
            vals['journal_id'] = bank_records[0]['journal_id'][0]
            vals['company_id'] = bank_records[0]['company_id'][0]
            # Set period_id from statement_date
            period_id = False
            if vals['date']:
                period_ids = period_model.find(
                    cr, uid, vals['date'], context=context)
                vals['period_id'] = period_ids and period_ids[0] or False
            statement_ids.append(
                self.pool.get('account.bank.statement').create(
                    cr, uid, vals, context=context))
        return statement_ids

    def process_none(self, cr, uid, data_file, context=None):
        raise osv.except_osv(
            _('Error'),
            _('No available format for importing bank statement.'
              ' You can install one of the file format available through the'
              ' module installation.')
        )

    def parse_file(self, cr, uid, ids, context=None):
        """ Process the file chosen in the wizard and returns a list view of the imported bank statements"""
        data = self.browse(cr, uid, ids[0], context=context)
        vals = getattr(self, "process_%s" % data.file_type)(cr, uid, data.data_file, context=context)
        statement_ids = self.import_bank_statement(cr, uid, vals, context=context)
        model, action_id = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'account', 'action_bank_statement_tree')
        action = self.pool[model].read(cr, uid, action_id, context=context)
        action['domain'] = "[('id', 'in', [" + ', '.join(map(str, statement_ids)) + "])]"
        return action

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
