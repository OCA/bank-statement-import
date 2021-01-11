# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models


class AccountBankStatementLine(models.Model):

    _inherit = "account.bank.statement.line"

    def write(self, vals):
        """
        Purpose of this hook is catch updates for records with name == '/'

        In reconciliation_widget_preprocess, there is attempt to assign
        partner into statement line, this assignment relies on name,
        during import name setup to '/' for records without it
        and this makes search results wrong and partner assignment randomly
        """
        if (
            self.env.context.get("no_reassign_empty_name")
            and len(self) == 1
            and len(vals.keys()) == 1
            and "partner_id" in vals
            and self.name == "/"
        ):
            return True
        return super().write(vals)
