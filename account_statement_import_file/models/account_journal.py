# Copyright 2004-2020 Odoo S.A.
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, api, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        formats_list = self._get_bank_statements_available_import_formats()
        if formats_list:
            res["bank_statements_source"] = "file_import_oca"
        return res

    def _get_bank_statements_available_import_formats(self):
        """Returns a list of strings representing the supported import formats."""
        return []

    def __get_bank_statements_available_sources(self):
        rslt = super().__get_bank_statements_available_sources()
        formats_list = self._get_bank_statements_available_import_formats()
        if formats_list:
            formats_list.sort()
            import_formats_str = ", ".join(formats_list)
            rslt.insert(
                0, ("file_import_oca", _("Import") + "(" + import_formats_str + ")")
            )
        return rslt

    def import_account_statement(self):
        """return action to import bank/cash statements.
        This button should be called only on journals with type =='bank'"""
        action = self.env["ir.actions.actions"]._for_xml_id(
            "account_statement_import_file.account_statement_import_action"
        )
        action["context"] = {"journal_id": self.id}
        return action
