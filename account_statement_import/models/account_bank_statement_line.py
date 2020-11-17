# Copyright 2004-2020 Odoo S.A.
# Copyright 2020 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import fields, models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    # Ensure transactions can be imported only once
    # (if the import format provides unique transaction ids)
    unique_import_id = fields.Char(string="Import ID", readonly=True, copy=False)
    # v13 field: bank_partner_id
    # This field was removed in v14, but it is still used in the code, cf the
    # method reconcile() !!! So I restore the field here
    partner_bank_id = fields.Many2one("res.partner.bank", string="Partner Bank Account")

    _sql_constraints = [
        (
            "unique_import_id",
            "unique(unique_import_id)",
            "A bank account transaction can be imported only once!",
        )
    ]
