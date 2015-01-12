# -*- coding: utf-8 -*-
"""Extend account.bank.statement.line."""
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


class AccountBankStatementLine(orm.Model):
    """Extend account.bank.statement.line (Transaction)."""
    _inherit = 'account.bank.statement.line'


    def _get_computed_fields(
            self, cr, uid, ids, field_names, args, context=None):
        """Compute values for functional fields."""
        res = {}
        for st_line in self.browse(cr, uid, ids, context=context):
            # Compute display value for bank account:
            bank_account_display = False
            if st_line.bank_account_id:
                bank_account_display = st_line.bank_account_id.name
            elif st_line.remote_account:
                bank_account_display = st_line.remote_account
            res[st_line.id] = {
                'bank_account_display': bank_account_display,
            }
        return res

    _columns = {
        'data': fields.text(
            'Original data from import',
            readonly=True,
        ),
        'transfer_type': fields.char(
            'Transfer type', size=32,
            readonly=True,
            help="""Action type that initiated this message""",
        ),
        'remote_account': fields.char(
            'Remote account', size=32,
            readonly=True,
            help="""The remote account as found in the import""",
        ),
        'remote_owner': fields.char(
            'Remote owner', size=32,
            readonly=True,
            help="""Owner as found in the import""",
        ),
        'bank_account_display': fields.function(
            _get_computed_fields,
            method=True,
            multi='computed_fields',
            string='Bank account',
            type='char', size=32,
        ),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
