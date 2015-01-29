# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
##############################################################################
#
#    Copyright (C) 2013 Therp BV (<http://therp.nl>)
#    All Rights Reserved
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
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
from openerp.osv import orm
from .camt import CamtParser as Parser


class AccountBankStatementImport(orm.Model):
    """Add process_camt method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.import'

    def _parse_file(self, cr, uid, data_file, context=None):
        """
        Parse a CAMT053 XML file
        """
        parser = Parser()
        try:
            os_statements = parser.parse(cr, data_file)
        except:
            # Not a camt file, returning super will call next candidate:
            return super(AccountBankStatementImport, self)._parse_file(
                cr, uid, data_file, context=context)
        # Succesfull parse, convert to format expected
        return self.convert_statements(
            cr, uid, os_statements, context=context)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
