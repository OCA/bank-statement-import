# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class AccountBankStatementImportMulti(models.TransientModel):

    _name = 'account.bank.statement.import.multi'

    data_file = fields.Binary(
        string='Bank Statements File',
        required=True,
    )
    filename = fields.Char()

    @api.multi
    def _get_files(self):
        """
        Must be inherited
        Return files available to import
        :return iterator of files
        """
        raise UserError(_(
            'Could not make sense of the given file.\n'
            'Did you install the module to support this type of file ?'))

    @api.multi
    def doit(self):
        self.ensure_one()
        statement_ids = []
        notifications = []
        for file in self._get_files():
            action = self.env["account.bank.statement.import"].create({
                "data_file": base64.b64encode(file),
            }).import_file()
            # import_file can return 2 things: a action to create a journal or
            # a action to open the reconciliation view
            unknown_bank_account = action["context"].get(
                "default_bank_acc_number")
            if unknown_bank_account:
                raise ValidationError(_(
                    "Journal %s doesn't exist") % unknown_bank_account)
            statement_ids.extend(action["context"]["statement_ids"])
            notifications.extend(action["context"]["notifications"])

        action = self.env.ref('account.action_bank_reconcile_bank_statements')
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications,
            },
            'type': 'ir.actions.client',
        }
