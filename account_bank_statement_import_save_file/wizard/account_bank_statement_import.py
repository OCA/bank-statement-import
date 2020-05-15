# Copyright 2015-2019 Therp BV (<http://therp.nl>).
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import base64

from odoo import api, fields, models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    current_data_file = fields.Binary(readonly=True)

    def _parse_file(self, data_file):
        res = super(AccountBankStatementImport, self)._parse_file(data_file)
        self.write({"current_data_file": base64.b64encode(data_file)})
        return res

    def _create_bank_statements(self, stmts_vals):
        res = super()._create_bank_statements(stmts_vals)
        if self.current_data_file and res[0]:
            statement_line = self.env["account.bank.statement.line"].browse(res[0][0])
            statement = statement_line.statement_id
            attach_vals = self._prepare_import_file_attachment(
                self.current_data_file, statement
            )
            attach = self.env["ir.attachment"].create(attach_vals)
            statement.write({"import_file": attach.id})
        return res

    @api.model
    def _prepare_import_file_attachment(self, current_data_file, statement):
        filename = "imported_bank_statement_file"
        return {
            "name": filename,
            "res_model": "account.bank.statement",
            "res_id": statement.id,
            "datas": current_data_file,
        }
