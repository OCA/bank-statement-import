# Copyright 2026 Daniel Lo Nigro <d@d.sb>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def open_action(self):
        action = super().open_action()
        provider = self.online_bank_statement_provider_id
        if (
            action.get("xml_id") == "account.action_credit_statement_tree"
            and provider
            and not provider.create_statement
        ):
            action = self.env["ir.actions.actions"]._for_xml_id(
                "account_reconcile_oca.action_bank_statement_line_reconcile_all"
            )
        return action
