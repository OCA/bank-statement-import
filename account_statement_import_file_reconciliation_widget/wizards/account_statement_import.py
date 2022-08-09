# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0).

from odoo import models


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def import_file_and_reconcile_button(self):
        """Process the file chosen in the wizard, create bank statement(s)
        and jump directly to the reconcilition widget"""
        result = self._import_file()
        statements = self.env["account.bank.statement"].browse(result["statement_ids"])
        statements.button_post()
        action = {
            "type": "ir.actions.client",
            "tag": "bank_statement_reconciliation_view",
            "context": {
                "statement_line_ids": statements.line_ids.ids,
                "company_ids": statements.company_id.ids,
                "notifications": result["notifications"],
            },
        }
        return action
