from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        """ Adds ofx to supported import formats.
        """
        rslt = super(
            AccountJournal,
            self)._get_bank_statements_available_import_formats()
        rslt.append('ofx')
        return rslt
