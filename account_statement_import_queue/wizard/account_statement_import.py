# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from typing import Any

from odoo import _, fields, models
from odoo.exceptions import ValidationError


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    statement_file = fields.Binary(required=False)

    def _import_file(self) -> Any:
        self.ensure_one()
        if not self.statement_file:
            raise ValidationError(_("Upload file before trying to import!"))
        return super()._import_file()

    def get_import_bank_statement_history_context(self) -> dict:
        """Build context for import bank statement history records."""
        ctx = dict(self.env.context or {})
        ctx.update(
            {
                "is_batch_import": True,
                "journal_id": self.journal_id.id,
                "active_id": self.journal_id.id,
            }
        )
        return ctx

    def action_import_batch(self) -> dict:
        """Create import history records for batch import processing."""
        statement_file_data = self.statement_file
        if not statement_file_data:
            raise ValidationError(_("Upload file before trying to import!"))
        vals_list = []
        ctx = self.get_import_bank_statement_history_context()

        # Create attachment for single file
        attachment_id = self.env["ir.attachment"].create(
            {
                "name": self.statement_filename,
                "type": "binary",
                "datas": statement_file_data,
                "res_model": "import.bank.statement.history",
            }
        )
        vals_list.append(
            {
                "name": self.statement_filename,
                "import_attachment_id": attachment_id.id,
                "res_model": "account.bank.statement",
                "context": ctx,
                "sheet_mapping_id": self.sheet_mapping_id.id,
                "journal_id": self.journal_id.id,
            }
        )

        # Batch create import history records
        import_bank_statement_history_rec = self.env[
            "import.bank.statement.history"
        ].create(vals_list)

        # Build action to open created records
        action_vals = {
            "name": self.env._("Import Bank Statement History"),
            "type": "ir.actions.act_window",
            "res_model": "import.bank.statement.history",
            "view_mode": "list",
            "context": {
                "create": False,
                "edit": False,
                "delete": False,
                "journal_id": self.journal_id.id,
            },
        }

        if import_bank_statement_history_rec:
            # Open single record in form view
            action_vals.update(
                {
                    "view_mode": "form",
                    "res_id": import_bank_statement_history_rec.id,
                }
            )
        return action_vals
