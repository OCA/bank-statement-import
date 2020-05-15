# Copyright 2015-2019 Therp BV (<http://therp.nl>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo import api, fields, models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    current_attachment_id = fields.Many2one("ir.attachment", readonly=True)

    def _parse_file(self, data_file):
        res = super(AccountBankStatementImport, self)._parse_file(data_file)
        attach_vals = self._prepare_import_file_attachment(data_file)
        attach = self.env["ir.attachment"].create(attach_vals)
        self.write({"current_attachment_id": attach.id})
        return res

    def _create_bank_statements(self, stmts_vals):
        res = super()._create_bank_statements(stmts_vals)
        attach = self.current_attachment_id
        if attach and res[0]:
            statement_line = self.env["account.bank.statement.line"].browse(res[0][0])
            attach.write(
                {
                    "res_model": "account.bank.statement",
                    "res_id": statement_line.statement_id.id,
                }
            )
        return res

    @api.model
    def _prepare_import_file_attachment(self, data_file):
        filename = "imported_bank_statement_file"
        return {
            "name": filename,
            "datas": base64.b64encode(data_file),
        }
