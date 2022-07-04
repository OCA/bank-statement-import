# Copyright 2022 Ecosoft Co., Ltd. (http://ecosoft.co.th)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountStatementImportSheetMappingWizard(models.TransientModel):
    _inherit = "account.statement.import.sheet.mapping.wizard"

    check_number_column = fields.Char(
        string="Check Number column",
    )

    def _get_mapping_values(self):
        res = super()._get_mapping_values()
        res.update({"check_number_column": self.check_number_column})
        return res
