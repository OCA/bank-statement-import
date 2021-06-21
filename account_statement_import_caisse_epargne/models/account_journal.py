from odoo import models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        res = super()._get_bank_statements_available_import_formats()
        res.append('CSV')
        return res
