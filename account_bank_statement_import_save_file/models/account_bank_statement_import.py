# Copyright 2015-2019 Therp BV (<http://therp.nl>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.multi
    def import_file(self):
        action = \
            super(AccountBankStatementImport, self).import_file()
        statement_ids = action.get('context', {}).get('statement_ids')
        notifications = action.get('context', {}).get('notifications')
        if statement_ids:
            attach_vals = self._prepare_import_file_attachment(
                self.data_file, statement_ids[0], notifications, self.filename)
            attach = self.env['ir.attachment'].create(attach_vals)
            self.env['account.bank.statement'].browse(statement_ids).write({
                'import_file': attach.id})
        return action

    @api.model
    def _prepare_import_file_attachment(self, data_file, statement_id,
                                        notifications, filename):
        if not filename:
            filename = '<unknown>'
        return {
            'name': filename,
            'res_model': 'account.bank.statement',
            'res_id': statement_id,
            'datas': data_file,
            'datas_fname': filename,
            'description': '\n'.join(
                '%(type)s: %(message)s' % notification
                for notification in notifications) or False,
        }
