# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class OnlineBankStatementPullWizard(models.TransientModel):
    _name = "online.bank.statement.pull.wizard"
    _description = "Online Bank Statement Pull Wizard"

    date_since = fields.Datetime(
        string="From",
        required=True,
        default=fields.Datetime.now,
    )
    date_until = fields.Datetime(
        string="To",
        required=True,
        default=fields.Datetime.now,
    )
    # The link to providers is Many2many, because you can select multiple
    # journals for the action to pull statements.
    provider_ids = fields.Many2many(
        string="Providers",
        comodel_name="online.bank.statement.provider",
        column1="wizard_id",
        column2="provider_id",
        relation="online_bank_statement_provider_pull_wizard_rel",
    )

    @api.model
    def default_get(self, fields_list):
        """Retrieve providers from the journals for which this wizard is launched."""
        res = super().default_get(fields_list)
        journal_ids = []
        if self.env.context.get("active_model") == "account.journal":
            if self.env.context.get("active_ids"):
                journal_ids = self.env.context["active_ids"]
            elif self.env.context.get("active_id"):
                journal_ids = [self.env.context["active_id"]]
        if journal_ids:
            journals = self.env["account.journal"].browse(journal_ids)
            res["provider_ids"] = [journals.online_bank_statement_provider_id.id]
        return res

    def action_pull(self):
        """Pull statements from providers and then show list of statements."""
        self.ensure_one()
        self.with_context(active_test=False).provider_ids._pull(
            self.date_since, self.date_until
        )
        action = self.env.ref("account.action_bank_statement_tree").sudo().read([])[0]
        if len(self.provider_ids) == 1:
            action["context"] = {
                "search_default_journal_id": self.provider_ids[0].journal_id.id
            }
        else:
            action["domain"] = [
                ("journal_id", "in", [o.journal_id.id for o in self.provider_ids])
            ]
        return action
