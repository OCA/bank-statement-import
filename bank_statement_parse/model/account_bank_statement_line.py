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
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
