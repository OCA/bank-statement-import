# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountBankStatement(models.Model):
    _inherit = "account.bank.statement"

    def unlink(self):
        lines = self.mapped("line_ids")
        res = super().unlink()
        lines.unlink()
        return res
