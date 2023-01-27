# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# Copyright 2023 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import fields, models


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

    def action_pull(self):
        """Pull statements from provider and then show list of statements."""
        self.ensure_one()
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")
        active_record = self.env[active_model].browse(active_id)
        if active_model == "account.journal":
            provider = active_record.online_bank_statement_provider_id
        else:
            provider = active_record
        provider._pull(self.date_since, self.date_until)
        action = self.env.ref("account.action_bank_statement_tree").sudo().read([])[0]
        action["domain"] = [("journal_id", "=", provider.journal_id.id)]
        return action
