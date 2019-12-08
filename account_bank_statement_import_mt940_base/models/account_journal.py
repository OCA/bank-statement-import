# Copyright 2019 OdooERP Romania <https://odooerpromania.ro>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models, _


class AccountJournal(models.Model):
    _inherit = "account.journal"

    def _get_bank_statements_available_import_formats(self):
        res = super(AccountJournal, self).\
            _get_bank_statements_available_import_formats()
        res.extend([_('mt940')])
        return res
