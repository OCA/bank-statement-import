# -*- coding: utf-8 -*-
# © 2015 Therp BV (<http://therp.nl>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64
from odoo import models, api


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.multi
    def import_file(self):
        action = \
            super(AccountBankStatementImport, self).import_file()
        statement_ids = action.get('context', {}).get('statement_ids')
        notifications = action.get('context', {}).get('notifications')
        data_file = base64.b64decode(self.data_file)
        if statement_ids:
            self.env['account.bank.statement'].browse(statement_ids).write({
                'import_file': self.env['ir.attachment'].create(
                    self._create_import_file_attachment_data(
                        data_file, statement_ids[0], notifications,
                        self.filename)).id,
            })
        return action

    @api.model
    def _create_import_file_attachment_data(self, data_file, statement_id,
                                            notifications, filename=None):
        return {
            'name': filename or '<unknown>',
            'res_model': 'account.bank.statement',
            'res_id': statement_id,
            'type': 'binary',
            'datas': base64.b64encode(data_file),
            'datas_fname': filename or '<unknown>',
            'description': '\n'.join(
                '%(type)s: %(message)s' % notification
                for notification in notifications) or False,
        }
