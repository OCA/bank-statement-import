# Copyright 2019-2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2019-2020 Dataplug (https://dataplug.io)
# Copyright 2023 Therp BV (https://therp.nl)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class AccountJournal(models.Model):
    _inherit = "account.journal"

    # Keep provider fields for compatibility with other modules.
    online_bank_statement_provider = fields.Selection(
        related="online_bank_statement_provider_id.service",
        readonly=False,
    )
    online_bank_statement_provider_id = fields.Many2one(
        string="Statement Provider",
        comodel_name="online.bank.statement.provider",
        copy=False,
    )

    def __get_bank_statements_available_sources(self):
        result = super().__get_bank_statements_available_sources()
        result.append(("online", _("Online (OCA)")))
        return result

    def _update_online_bank_statement_provider_id(self, service):
        """Automatically create service.

        This method exists for compatibility reasons. The preferred method
        to create an online provider is directly through the menu,
        """
        OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        for journal in self:
            if (
                journal.online_bank_statement_provider_id
                and journal.online_bank_statement_provider == service
            ):
                _logger.info(
                    "Journal %s already linked to service %s", journal.name, service
                )
                # Provider already exists.
                continue
            # Use existing or create new provider for service.
            provider = OnlineBankStatementProvider.search(
                [
                    ("journal_id", "=", journal.id),
                    ("service", "=", service),
                ],
                limit=1,
            ) or OnlineBankStatementProvider.create(
                {
                    "journal_id": journal.id,
                    "service": service,
                }
            )
            journal.online_bank_statement_provider_id = provider
            _logger.info("Journal %s now linked to service %s", journal.name, service)

    @api.model
    def create(self, vals):
        self._update_vals(vals)
        service = self._get_service(vals)
        rec = super().create(vals)
        if service:
            rec._update_online_bank_statement_provider_id(service)
        return rec

    def write(self, vals):
        self._update_vals(vals)
        service = self._get_service(vals)
        res = super().write(vals)
        if service:
            self._update_online_bank_statement_provider_id(service)
        return res

    def _update_vals(self, vals):
        """Ensure consistent values."""
        if (
            "bank_statements_source" in vals
            and vals.get("bank_statements_source") != "online"
        ):
            vals["online_bank_statement_provider_id"] = False

    def _get_service(self, vals):
        """Check wether user wants to create service."""
        return (
            vals.pop("online_bank_statement_provider")
            if "online_bank_statement_provider" in vals
            else False
        )

    def action_online_bank_statements_pull_wizard(self):
        """This method is also kept for compatibility reasons."""
        self.ensure_one()
        provider = self.online_bank_statement_provider_id
        return provider.action_online_bank_statements_pull_wizard()
