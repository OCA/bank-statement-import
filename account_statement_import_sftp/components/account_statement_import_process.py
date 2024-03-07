# Copyright 2023 Compassion CH
# @author: Simon Gonzalez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _
from odoo.tools import str2bool

from odoo.addons.component.core import Component


class EdiBankStatementImportProcess(Component):
    _name = "edi.input.process.bank.statement.import"
    _usage = "input.process"
    _backend_type = "bk_sftp_imp"
    _inherit = "edi.component.input.mixin"

    def process(self):
        ir_config = self.env["ir.config_parameter"].sudo()
        auto_post = str2bool(ir_config.get_param("import_statement_edi_auto_post"))
        statement_import = self.env["account.statement.import"].create(
            [
                {
                    "statement_file": self.exchange_record.exchange_file,
                    "statement_filename": self.exchange_record.exchange_filename,
                }
            ]
        )
        action = statement_import.import_file_button()
        if not action:
            raise ValueError(_("The import didn't succeed."))
        statement = self.env["account.bank.statement"].browse(action.get("res_id"))
        if not (statement.state and statement.state in ["posted", "open"]):
            raise ValueError(_("The bank statement could not be validated."))
        if auto_post:
            statement.button_post()
