# -*- coding: utf-8 -*-
"""Extend account.bank.statement."""
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


class AccountBankStatement(orm.Model):
    """Extend account.bank.statement."""
    _inherit = 'account.bank.statement'

    def get_unique_statement_id(self, cr, base):
        """Generate unique identifier for bank_statement using
        autonumbering."""
        name = base
        suffix = 1
        while True:
            cr.execute(
                "select id from account_bank_statement where name = %s",
                (name,))
            if not cr.rowcount:
                break
            suffix += 1
            name = "%s-%d" % (base, suffix)
        return name

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
