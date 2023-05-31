# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountBankStatementClearPartner(models.Model):
    _inherit = "account.bank.statement"

    def clear_partners(self):
        for rec in self:
            for line in rec.line_ids:
                if not line.is_reconciled:
                    line.write({"partner_id": False})
