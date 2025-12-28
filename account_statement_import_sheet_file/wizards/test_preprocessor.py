# Copyright 2026 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>

import base64

from odoo import api, fields, models


class AccountStatementImportSheetPreprocessor(models.TransientModel):
    _name = "account.statement.import.sheet.preprocessor"
    _description = "Bank Statement Import Sheet Preprocessor Wizard"

    mapping_id = fields.Many2one(
        "account.statement.import.sheet.mapping", required=True
    )
    preprocessor_code = fields.Text(
        related="mapping_id.preprocessor_code", readonly=False
    )
    test_file = fields.Binary(required=True)
    test_result = fields.Text(compute="_compute_test_result")

    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if (
            self.env.context.get("active_model")
            == "account.statement.import.sheet.mapping"
        ):
            res["mapping_id"] = self.env.context.get("active_id")
        return res

    @api.depends("mapping_id", "preprocessor_code", "test_file")
    def _compute_test_result(self):
        for rec in self:
            if rec.mapping_id and rec.preprocessor_code and rec.test_file:
                try:
                    file_data = base64.b64decode(rec.test_file)
                    rec.test_result = rec.mapping_id._preprocess(file_data)
                except Exception as e:
                    rec.test_result = str(e)
            else:
                rec.test_result = False
