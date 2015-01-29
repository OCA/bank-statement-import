# -*- coding: utf-8 -*-
"""Extend account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2015 Therp BV <http://therp.nl>.
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
from openerp.osv import osv


class AccountBankStatementImport(osv.TransientModel):
    """Extend model account.bank.statement.import.

    Override parser for import files to actually store imported file and
    import log in the database.
    """
    _inherit = 'account.bank.statement.import'

    def import_file(self, cr, uid, ids, context=None):
        """Override base class to store file and notifications."""
        res = super(AccountBankStatementImport, self).import_file(
            cr, uid, ids, context=context)
        user_model = self.pool['res.users']
        attachment_model = self.pool['ir.attachment']
        history_model = self.pool['bank.statement.import.history']
        # Create history record:
        user_record = user_model.read(
            cr, uid, [uid], ['company_id'], context=context)[0]
        notifications = res['context']['notifications'] or False
        history_vals = {
            'company_id': user_record['company_id'][0],
            'log': notifications
        }
        new_id = history_model.create(
            cr, uid, history_vals, context=context)
        # Create attachment for imported file
        data_file = self.browse(cr, uid, ids[0], context=context).data_file
        attachment_vals = {
            'name': 'Created by import',
            'res_model': history_model._name,
            'res_id': new_id,
            'datas': data_file
        }
        attachment_id = attachment_model.create(
            cr, uid, attachment_vals, context=context)
        history_model.write(
            cr, uid, [new_id], {'attachment_id': attachment_id},
            context=context
        )
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
