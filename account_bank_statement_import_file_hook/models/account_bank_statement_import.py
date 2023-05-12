# Copyright 2023 ForgeFlow, S.L.
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo import models


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _post_process_statements(self, data_file, statement_line_ids):
        """To be inherited"""
        return False
