# -*- coding: utf-8 -*-
"""Create history file for bank statement imports"""
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
from openerp import fields, models


class BankStatementHistory(models.Model):
    """Imported Bank Statements File"""
    _name = 'bank.statement.import.history'
    _description = __doc__
    _rec_name = 'date'

    company_id = fields.Many2one(
        string='Company',
        comodel_name='res.company',
        readonly=True
    )
    date = fields.Datetime(
        string='Import Date',
        readonly=True,
        default=fields.Datetime.now
    )
    log = fields.Text(
        string='Import Log',
        readonly=True
    )
    attachment_id = fields.Many2one(
        string='Imported file',
        comodel_name='ir.attachment',
        readonly=True
    )

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
