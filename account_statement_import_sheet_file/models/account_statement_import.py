# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _get_default_mapping_id(self):
        return (
            self.env["account.journal"]
            .browse(self.env.context.get("journal_id"))
            .default_sheet_mapping_id
        )

    sheet_mapping_id = fields.Many2one(
        string="Sheet mapping",
        comodel_name="account.statement.import.sheet.mapping",
        default=_get_default_mapping_id,
    )
    mapping_template_datas = fields.Binary(
        string="Template File",
        related="sheet_mapping_id.template_datas",
    )
    mapping_template_fname = fields.Char(
        string="Template File Name", related="sheet_mapping_id.template_fname"
    )
    statement_file = fields.Binary(required=False)

    def get_import_sample(self) -> dict:
        self.ensure_one()
        return {
            "name": self.env._("Import Bank Statement File"),
            "type": "ir.actions.act_window",
            "res_model": "account.statement.import",
            "view_mode": "form",
            "res_id": self.id,
            "views": [(False, "form")],
            "target": "new",
            "context": self.env.context.copy(),
        }

    def _parse_file(self, data_file):
        self.ensure_one()
        if self.sheet_mapping_id:
            try:
                Parser = self.env["account.statement.import.sheet.parser"]
                return Parser.parse(
                    data_file, self.sheet_mapping_id, self.statement_filename
                )
            except BaseException as exc:
                if self.env.context.get("account_statement_import_sheet_file_test"):
                    raise
                _logger.warning("Sheet parser error", exc_info=True)
                raise UserError(self.env._("Bad file/mapping: ") + str(exc)) from exc
        return super()._parse_file(data_file)

    def _create_bank_statements(self, stmts_vals, result):
        """Set balance_end_real if not already provided by the file."""
        res = super()._create_bank_statements(stmts_vals, result)
        statements = self.env["account.bank.statement"].browse(result["statement_ids"])
        for statement in statements:
            if not statement.balance_end_real:
                amount = sum(statement.line_ids.mapped("amount"))
                statement.balance_end_real = statement.balance_start + amount
        return res
