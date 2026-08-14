# Copyright 2025 Simone Rubino
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).


from odoo.addons.account_statement_import_sheet_file.tests.common import (
    Common as ImportCommon,
)


class Common(ImportCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.module = "account_statement_import_sheet_html_file"
