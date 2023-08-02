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
    )

    is_ofx_provider = fields.Boolean()

    @api.onchange("date_since")
    def _compute_is_ofx_provider(self):
        provider_model = self.env["online.bank.statement.provider"]
        active_id = self.env.context.get("active_id")
        provider = provider_model.browse(active_id)
        self.is_ofx_provider = provider.service == "OFX"

    def action_pull(self):
        return super(
            OnlineBankStatementPullWizard,
            self.with_context(ofx_institution_ids=self.ofx_institution_ids.ids),
        ).action_pull()
