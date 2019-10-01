# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    statement_import_txt_map_id = fields.Many2one(
        comodel_name='account.bank.statement.import.map',
        string='Statement Import Txt Map',
    )

    def _get_bank_statements_available_import_formats(self):
        res = super()._get_bank_statements_available_import_formats()
        res.append('Txt')
        return res
