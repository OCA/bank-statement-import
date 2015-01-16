# -*- coding: utf-8 -*-
"""Extend account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
#
#    All other contributions are (C) by their respective contributors
#
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
from openerp.osv import orm, fields
from openerp.tools.translate import _


class AccountBankStatementImport(orm.Model):
    """Imported Bank Statements File

    Unlike backported standard Odoo model, this is not a transient model,
    because we want to save the import files for debugging and accounting
    purposes.
    """
    _inherit = 'account.bank.statement.import'
    _description = __doc__
    _rec_name = 'date'

    def detect_partner_and_bank(
            self, cr, uid, transaction_vals=None, partner_vals=None,
            bank_vals=None, context=None):
        """Try to find a partner and bank_account for a transaction.

        The calling function has to pass all the information it can gather
        from the imported transaction. This function will try several
        searches to find an existing bank account and partner. But possibly
        only the partner is found. In that case, a bank account might be
        automatically created if the information is there, and it is certain
        the transaction can not be for one of the existing bank accounts of
        the partner.

        The following searches will be done (if needed information present):
        - Search on bank account number;
        - Search on partner name and address info;  # NOT IMPLEMENTED
        - Search only on partner name (should be unique);
        - Search only on address info (should be unique and complete enough);
          # NOT IMPLEMENTED
        - Search invoices and moves with reference info (should be unique).
          # NOT IMPLEMENTED
        """
        partner_id = False
        bank_account_id = False
        bank_model = self.pool['res.partner.bank']
        partner_model = self.pool['res.partner']
        country_model = self.pool['res.country']
        acc_number = (
            'acc_number' in bank_vals and bank_vals['acc_number'] or False)
        acc_name = (
            'acc_name' in partner_vals and partner_vals['acc_name'] or False)
        # Search on bank account number
        if acc_number:
            ids = bank_model.search(
                cr, uid, [('acc_number', '=', acc_number)], context=context)
            if ids:
                # Bank accounts should be unique!
                assert len(ids) == 1, (
                    _('More then one bank account with number %s!') %
                    acc_number
                )
                bank_account_id = ids[0]
                bank_records = bank_model.read(
                    cr, uid, ids, ['partner_id'], context=context)
                partner_id = bank_records[0]['partner_id']
            else:
                # Create the bank account, not linked to any partner.
                # The reconciliation will link the partner manually
                # chosen at the bank statement final confirmation time.
                if bank_model.is_iban_valid(
                        cr, uid, acc_number, context=context):
                    bank_code = 'iban'
                else:
                    bank_code = 'bank'
                bank_vals.update({
                    'acc_number': acc_number,
                    'state': bank_code,
                })
                # Try to find country, if passed
                if 'country_code' in bank_vals:
                    country_code = bank_vals['country_code']
                    if country_code:  # Might be False
                        country_ids = country_model.search(
                            cr, uid, [('code', '=', country_code.upper())],
                            context=context
                        )
                        if country_ids:
                            bank_vals['country_id'] = country_ids[0]
                    del bank_vals['country_code']  # Not in model
                bank_account_id = bank_model.create(
                    cr, uid, bank_vals, context=context)
        # Search on partner data
        if (not partner_id) and acc_name:
            ids = partner_model.search(
                cr, uid, [('name', '=', acc_name)], context=context
            )
            if len(ids) == 1:
                # TODO Should warn or raise if > 1
                partner_id = ids[0]
                # If we found a partner now, and we had a bank account
                # withouth partner, then link the two now:
                if bank_account_id:
                    bank_model.write(
                        cr, uid, [bank_account_id],
                        {'partner_id': partner_id}, context=context
                    )
        return bank_account_id, partner_id

    _columns = {
        'company_id': fields.many2one(
            'res.company',
            'Company',
            select=True,
            readonly=True,
        ),
        'date': fields.datetime(
            'Import Date',
            readonly=True,
            select=True,
        ),
        # Old field format replaced by file_type
        # 'file_name': fields.char('File name', size=256),
        'log': fields.text(
            'Import Log',
            readonly=True,
        ),
        'state': fields.selection(
            [
                ('unfinished', 'Unfinished'),
                ('error', 'Error'),
                ('review', 'Review'),
                ('ready', 'Finished'),
            ],
            'State',
            select=True,
            readonly=True,
        ),
    }
    _defaults = {
        'date': fields.date.context_today,
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
