# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

from odoo import models


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def import_file_and_reconcile_button(self):
        """Process the file chosen in the wizard, create bank statement(s)
        and jump directly to the reconciliation widget"""
        result = self._import_file()
        self.env["account.bank.statement"].browse(result["statement_ids"])
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account_reconcile_oca.action_bank_statement_line_reconcile"
        )
        action["context"] = {
            "default_journal_id": self._context.get("journal_id"),
            "active_id": self._context.get("journal_id"),
            "search_default_not_reconciled": True,
            "view_ref": "account_reconcile_oca.bank_statement_line_form_reconcile_view",
        }
        if result["notifications"]:
            action_with_notif = {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "type": "warning",
                    "sticky": True,
                    "message": "\n\n".join(result["notifications"]),
                    "next": action,
                },
            }
            return action_with_notif
        return action
