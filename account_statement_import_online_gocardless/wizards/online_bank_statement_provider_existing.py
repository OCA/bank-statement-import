# Copyright 2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


class OnlineBankStatementProviderExisting(models.TransientModel):
    _name = "online.bank.statement.provider.existing"
    _description = "Wizard for reusing existing GoCardless provider"
    _rec_name = "provider_id"

    provider_id = fields.Many2one(comodel_name="online.bank.statement.provider")
    other_provider_id = fields.Many2one(comodel_name="online.bank.statement.provider")

    def link_existing(self):
        provider = self.provider_id
        other = self.other_provider_id
        provider.write(
            {
                "gocardless_requisition_ref": other.gocardless_requisition_ref,
                "gocardless_requisition_id": other.gocardless_requisition_id,
                "gocardless_requisition_expiration": (
                    other.gocardless_requisition_expiration
                ),
                "gocardless_institution_id": other.gocardless_institution_id,
            }
        )
        provider._gocardless_finish_requisition(dry=True)

    def new_link(self):
        return self.provider_id._gocardless_select_bank_institution()
