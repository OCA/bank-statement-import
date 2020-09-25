# Copyright 2020 Tecnativa - João Marques
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountBankStatementClearPartner(models.Model):
    _inherit = "account.bank.statement"

    def clear_partners(self):
        self.mapped("line_ids").filtered(
            lambda x: not x.journal_entry_ids and not x.account_id
        ).write({"partner_id": False})
