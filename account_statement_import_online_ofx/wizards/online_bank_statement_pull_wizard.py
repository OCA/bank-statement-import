# Copyright 2023 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models


class OnlineBankStatementPullWizard(models.TransientModel):
    _inherit = "online.bank.statement.pull.wizard"

    ofx_institution_ids = fields.Many2many(
        string="OFX Institutions",
        comodel_name="ofx.institution.line",
        column1="wizard_id",
        column2="institution_line_id",
        relation="ofx_institution_line_pull_wizard_rel",
        domain="[('provider_id','in',provider_ids)]",
    )
    is_ofx_provider = fields.Boolean()

    @api.onchange("provider_ids")
    def onchange_provider_ids(self):
        for rec in self:
            rec.is_ofx_provider = False
            for provider in rec.provider_ids:
                if provider.service == "OFX":
                    rec.is_ofx_provider = True
                    break

    def action_pull(self):
        return super(
            OnlineBankStatementPullWizard,
            self.with_context(ofx_institution_ids=self.ofx_institution_ids.ids),
        ).action_pull()
