# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

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

    def _parse_file(self, data_file):
        self.ensure_one()
        try:
            Parser = self.env["account.statement.import.sheet.parser"]
            return Parser.parse(data_file, self.sheet_mapping_id)
        except BaseException:
            if self.env.context.get("account_statement_import_txt_xlsx_test"):
                raise
            _logger.warning("Sheet parser error", exc_info=True)
        return super()._parse_file(data_file)
