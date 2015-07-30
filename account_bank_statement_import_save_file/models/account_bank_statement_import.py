# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    This module copyright (C) 2015 Therp BV (<http://therp.nl>).
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
import base64
from openerp import models, api


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _import_file(self, data_file):
        (statement_ids, notifications) = \
            super(AccountBankStatementImport, self)._import_file(data_file)
        if statement_ids:
            self.env['account.bank.statement'].browse(statement_ids).write({
                'import_file': self.env['ir.attachment'].create(
                    self._create_import_file_attachment_data(
                        data_file, statement_ids[0], notifications)).id,
            })
        return (statement_ids, notifications)

    @api.model
    def _create_import_file_attachment_data(self, data_file, statement_id,
                                            notifications):
        return {
            'name': '<unknown>',
            'res_model': 'account.bank.statement',
            'res_id': statement_id,
            'type': 'binary',
            'datas': base64.b64encode(data_file),
            'description': notifications,
        }
