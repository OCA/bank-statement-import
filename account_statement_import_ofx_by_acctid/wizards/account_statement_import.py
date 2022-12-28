# Copyright 2022 - TODAY, Marcel Savegnago <marcel.savegnago@escodoo.com.br>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64

from odoo import _, api, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number


class AccountStatementImport(models.TransientModel):

    _inherit = "account.statement.import"

    @api.model
    def _match_journal(self, account_number, currency):
        journal_obj = self.env["account.journal"]

        file_data = base64.b64decode(self.statement_file)
        if self._check_ofx(file_data):
            sanitized_account_number = sanitize_account_number(account_number)

            journal = journal_obj.search(
                [
                    ("type", "=", "bank"),
                    (
                        "bank_account_id.sanitized_acctid",
                        "ilike",
                        sanitized_account_number,
                    ),
                ],
                limit=1,
            )
            journal_id = self.env.context.get("journal_id")
            if journal_id and journal.id != journal_id:
                raise UserError(
                    _(
                        "The journal found for the file is not consistent with the "
                        "selected journal. You should use the proper journal or "
                        "use the generic button on the top of the Accounting Dashboard"
                    )
                )
            if journal:
                account_number = journal.bank_acc_number

        return super()._match_journal(account_number=account_number, currency=currency)
