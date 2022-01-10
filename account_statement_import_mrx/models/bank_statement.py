# Copyright 2022 AGEPoly
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountBankStatement(models.Model):

    _inherit = "account.bank.statement"

    def reconciliation_widget_preprocess(self):
        return super(
            AccountBankStatement, self.with_context(no_reassign_empty_name=True)
        ).reconciliation_widget_preprocess()
