# -*- coding: utf-8 -*-
##############################################################################
#
#    Copyright (C) 2009 EduSense BV (<http://www.edusense.nl>).
#              (C) 2011 - 2013 Therp BV (<http://therp.nl>).
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
'''
'''
import re
from openerp.osv import orm, fields
from openerp.tools.translate import _


class account_banking_imported_file(orm.Model):
    '''Imported Bank Statements File
    
    Unlike backported standard Odoo model, this is not a transient model, 
    because we want to save the import files for debugging and accounting
    purposes.
    '''
    _inherit = 'account.bank.statement.import'
    _description = __doc__
    _rec_name = 'date'

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


