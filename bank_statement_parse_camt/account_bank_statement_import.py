# -*- coding: utf-8 -*-
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
from openerp.addons.bank_statement_parse import parser_types
from openerp.addons.bank_statement_parse.lib import advanced_parser
from camt import CamtParser as Parser


parser_types.add_file_type(('camt', 'Generic CAMT Format'))


class account_bank_statement_import(orm.Model):
    _inherit='account.bank.statement.import'

    @advanced_parser
    def process_camt(self, cr, data):
        """
        Parse a CAMT053 XML file
        """
        parser = Parser()
        return parser.parse(cr, data)
