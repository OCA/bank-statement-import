# Copyright 2004-2020 Odoo S.A.
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import _, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """Returns a list of strings representing the supported import formats."""
        return []

    def __get_bank_statements_available_sources(self):
        rslt = super().__get_bank_statements_available_sources()
        formats_list = self._get_bank_statements_available_import_formats()
        if formats_list:
            formats_list.sort()
            import_formats_str = ", ".join(formats_list)
            rslt.append(("file_import", _("Import") + "(" + import_formats_str + ")"))
        return rslt

    def import_statement(self):
        """return action to import bank/cash statements.
        This button should be called only on journals with type =='bank'"""
        action = (
            self.env.ref("account_statement_import.account_statement_import_action")
            .sudo()
            .read()[0]
        )
        action["context"] = {"journal_id": self.id}
        return action
