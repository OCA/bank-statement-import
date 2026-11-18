# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
import logging
import secrets

from markupsafe import escape

from odoo import _, fields, models
from odoo.exceptions import UserError

from ..models.finapi_interface import FinapiApiError

_logger = logging.getLogger(__name__)


class FinapiWebformWizard(models.TransientModel):
    _name = "finapi.webform.wizard"
    _description = "finAPI Web Form 2.0 Wizard"

    provider_id = fields.Many2one(
        "online.bank.statement.provider",
        string="Provider",
        required=True,
        readonly=True,
    )
    mode = fields.Selection(
        [
            ("import", "Import new bank connection"),
            ("reconnect", "Link existing finAPI account"),
            ("update", "Update existing / renew consent"),
        ],
        default="import",
        required=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("waiting", "Waiting for user"),
            ("account_select", "Select account"),
            ("done", "Done"),
        ],
        default="draft",
        readonly=True,
    )
    webform_id = fields.Char(readonly=True)
    webform_url = fields.Char(string="Open this URL to authorise", readonly=True)
    webform_status = fields.Char(readonly=True)
    # finAPI int64 id stored as Char (see provider model for rationale).
    bank_connection_id = fields.Char(readonly=True)

    # Account picking (populated after COMPLETED)
    account_ids = fields.One2many(
        "finapi.webform.wizard.account",
        "wizard_id",
    )
    selected_account_id = fields.Many2one(
        "finapi.webform.wizard.account",
        string="Account to link",
        domain="[('wizard_id', '=', id)]",
        help="Select the account to link to this provider's journal.",
    )
    multi_link = fields.Boolean(
        string="Link all accounts",
        help="Create a new provider for every account from this "
        "bank connection (one provider per journal).",
    )

    info = fields.Html(readonly=True, sanitize=False)

    # -------------------------------------------------------------------
    # Step 1: create web form (or fetch existing connections)
    # -------------------------------------------------------------------
    def action_start(self):
        self.ensure_one()
        if self.mode == "reconnect":
            return self._action_start_reconnect()
        return self._action_start_webform()

    def _action_start_reconnect(self):
        """Fetch all existing bank connections and their accounts from
        finAPI and jump straight to account selection — no Web Form needed."""
        provider = self.provider_id
        with provider._finapi_get_interface() as interface:
            token = provider._finapi_get_user_token(interface)
            connections = interface.list_bank_connections(token)
            if not connections:
                raise UserError(
                    _(
                        "No existing bank connections found for this finAPI "
                        "user. Use 'Import new bank connection' instead."
                    )
                )
            # Collect all accounts from all connections
            self.account_ids.unlink()
            rows = []
            for bc in connections:
                bc_id = bc.get("id")
                accounts = interface.list_accounts(token, bc_id)
                for acc in accounts:
                    rows.append(
                        (
                            0,
                            0,
                            {
                                "finapi_account_id": str(acc.get("id") or ""),
                                "bank_connection_id": str(bc_id or ""),
                                "iban": acc.get("iban")
                                or acc.get("accountNumber")
                                or "",
                                "name": acc.get("accountHolderName")
                                or acc.get("accountName")
                                or "",
                                "account_type": acc.get("accountTypeName")
                                or acc.get("accountType")
                                or "",
                                "balance": acc.get("balance") or 0.0,
                                "currency": acc.get("currency") or "",
                            },
                        )
                    )
        if not rows:
            raise UserError(_("No accounts found in existing bank connections."))
        self.write(
            {
                "account_ids": rows,
                "state": "account_select",
                "info": _(
                    "<p>Select the existing finAPI account to link to "
                    "this Odoo bank journal.</p>"
                ),
            }
        )
        return self._reopen()

    def _get_webhook_secret(self):
        """Return the shared webhook secret, generating it on first use.

        The secret is embedded in the callback URL registered at finAPI and
        verified by the webhook controller, so that arbitrary third parties
        cannot post fake callbacks.
        """
        icp = self.env["ir.config_parameter"].sudo()
        secret = icp.get_param("finapi.webhook_secret")
        if not secret:
            secret = secrets.token_urlsafe(32)
            icp.set_param("finapi.webhook_secret", secret)
        return secret

    def _get_webform_urls(self):
        """Return ``(redirect_url, callback_url)`` for the web form.

        finAPI requires redirectUrl to be HTTPS — skip if not available.
        """
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url", "")
        if base and base.startswith("https://"):
            secret = self._get_webhook_secret()
            return (
                f"{base}/finapi/webform/return",
                f"{base}/finapi/webform/callback?secret={secret}",
            )
        return None, None

    @staticmethod
    def _is_redirect_not_allowed_error(exc):
        """True when finAPI rejected the call because the mandator license
        does not allow redirect/callback URLs (e.g. UNLICENSED sandbox)."""
        message = str(exc)
        return "INVALID_REDIRECT_URL" in message or "UNLICENSED" in message

    def _create_webform(self, interface, token, redirect_url, callback_url):
        """Create the web form for the current mode.

        In ``update`` mode, fall back to a fresh import web form when the
        existing bank connection is not updatable. License errors about
        redirect URLs are re-raised so the caller can retry without URLs.
        """
        provider = self.provider_id
        if self.mode == "update":
            try:
                return interface.create_webform_update(
                    token,
                    provider.finapi_bank_connection_id,
                    redirect_url=redirect_url,
                    callback_url=callback_url,
                )
            except FinapiApiError as exc:
                if self._is_redirect_not_allowed_error(exc):
                    raise
                # e.g. bank connection no longer updatable — a fresh import
                # web form achieves the same result for the user.
                _logger.info(
                    "bankConnectionUpdate not available (%s), "
                    "falling back to bankConnectionImport",
                    exc,
                )
        return interface.create_webform_import(
            token,
            redirect_url=redirect_url,
            callback_url=callback_url,
        )

    def _action_start_webform(self):
        """Create a finAPI Web Form for import or update."""
        provider = self.provider_id
        redirect_url, callback_url = self._get_webform_urls()
        with provider._finapi_get_interface() as interface:
            token = provider._finapi_get_user_token(interface)
            try:
                payload = self._create_webform(
                    interface, token, redirect_url, callback_url
                )
            except FinapiApiError as exc:
                if not (redirect_url or callback_url) or not (
                    self._is_redirect_not_allowed_error(exc)
                ):
                    raise
                # UNLICENSED (sandbox) mandators may not pass redirectUrl /
                # callbacks at all — retry without them. The user then simply
                # closes the finAPI tab manually and clicks "Refresh status".
                _logger.info(
                    "finAPI license does not allow redirect/callback URLs "
                    "(%s) — retrying without them.",
                    exc,
                )
                payload = self._create_webform(interface, token, None, None)
        self.write(
            {
                "webform_id": payload.get("id"),
                "webform_url": payload.get("url"),
                "webform_status": payload.get("status") or "NOT_YET_OPENED",
                "state": "waiting",
                "info": _(
                    "<p>Open the URL below in a new tab, authorise with your bank, "
                    "and complete the 2-factor authentication. "
                    "When done, come back here and click <b>Refresh status</b>.</p>"
                ),
            }
        )
        provider.sudo().write({"finapi_last_webform_id": payload.get("id")})
        return self._reopen()

    # -------------------------------------------------------------------
    # Step 2: poll status
    # -------------------------------------------------------------------
    def action_refresh(self):
        self.ensure_one()
        if not self.webform_id:
            raise UserError(_("No web form to refresh."))
        provider = self.provider_id
        with provider._finapi_get_interface() as interface:
            token = provider._finapi_get_user_token(interface)
            payload = interface.get_webform(token, self.webform_id)
            status = payload.get("status") or "UNKNOWN"
            self.webform_status = status

            if status == "COMPLETED":
                bc_id = (payload.get("payload") or {}).get("bankConnectionId")
                if not bc_id:
                    raise UserError(
                        _(
                            "Web form completed but finAPI did not return a "
                            "bankConnectionId."
                        ),
                    )
                self.bank_connection_id = str(bc_id)
                self._populate_accounts(interface, token, bc_id)
                self.state = "account_select"
                self.info = _(
                    "<p>Bank authorised. Select which account should be linked "
                    "to this Odoo bank journal.</p>"
                )
        if status in ("COMPLETED_WITH_ERROR", "ABORTED", "EXPIRED"):
            self.state = "done"
            self.info = _(
                "<p>Web form ended in status <b>%s</b>. " "Please start a new one.</p>"
            ) % escape(status)
        elif status != "COMPLETED":
            self.info = _(
                "<p>Current status: <b>%s</b>. Keep the bank tab open until the "
                "authorisation is finished, then click Refresh again.</p>"
            ) % escape(status)
        return self._reopen()

    # -------------------------------------------------------------------
    # Step 3: apply selected account(s)
    # -------------------------------------------------------------------
    def action_apply(self):
        self.ensure_one()
        if self.multi_link:
            return self._apply_multi()
        if not self.selected_account_id:
            raise UserError(_("Pick an account first."))
        self._link_account(self.provider_id, self.selected_account_id)
        self.state = "done"
        self.info = _(
            "<p>Done. Account <b>%(iban)s</b> linked. "
            "Transactions will be pulled by the scheduled job.</p>"
        ) % {"iban": escape(self.selected_account_id.iban or "")}
        return self._reopen()

    def _apply_multi(self):
        """Link every fetched account — the first one to the current
        provider, additional ones each get a new provider + journal."""
        if not self.account_ids:
            raise UserError(_("No accounts available to link."))
        first = True
        linked = []
        for acc in self.account_ids:
            if first:
                self._link_account(self.provider_id, acc)
                first = False
            else:
                new_provider = self._create_provider_for_account(acc)
                self._link_account(new_provider, acc)
            linked.append(acc.iban or str(acc.finapi_account_id))
        self.state = "done"
        self.info = _(
            "<p>Done. %(count)s account(s) linked: "
            "<b>%(accounts)s</b>. "
            "Transactions will be pulled by the scheduled job.</p>"
        ) % {
            "count": len(linked),
            "accounts": escape(", ".join(linked)),
        }
        return self._reopen()

    def _link_account(self, provider, acc):
        """Write bank connection + account to the given provider."""
        bc_id = acc.bank_connection_id or self.bank_connection_id
        provider.sudo().write(
            {
                "finapi_bank_connection_id": bc_id,
                "finapi_account_id": acc.finapi_account_id,
            }
        )
        # refresh consent expiry silently — must never block the linking
        try:
            provider.action_finapi_check_connection()
        except UserError as exc:
            # FinapiApiError / FinapiAuthError are UserError subclasses
            _logger.info("Consent check after webform failed: %s", exc)

    def _create_provider_for_account(self, acc):
        """Create a new journal + provider for an additional account.

        The journal is created with ``online_bank_statement_provider`` set,
        so the OCA base module auto-creates and links the provider record
        (see ``account.journal._update_providers``). The journal code is
        auto-generated by core when omitted.
        """
        src = self.provider_id
        # sudo: secret fields are restricted to base.group_system, but
        # accounting managers must be able to roll out additional accounts.
        src_sudo = src.sudo()
        company = src.journal_id.company_id
        journal_vals = {
            "name": f"finAPI {acc.iban or acc.finapi_account_id}",
            "type": "bank",
            "company_id": company.id,
            "bank_statements_source": "online",
            "online_bank_statement_provider": "finapi",
        }
        if acc.currency:
            currency = (
                self.env["res.currency"]
                .with_context(active_test=False)
                .search([("name", "=", acc.currency)], limit=1)
            )
            if currency and currency != company.currency_id:
                journal_vals["currency_id"] = currency.id
        journal = self.env["account.journal"].create(journal_vals)
        provider = self._get_or_create_provider_for_journal(journal)
        provider.sudo().write(
            {
                "finapi_environment": src.finapi_environment,
                "finapi_base_url": src.finapi_base_url,
                "finapi_webform_base_url": src.finapi_webform_base_url,
                "finapi_client_id": src.finapi_client_id,
                "finapi_client_secret": src_sudo.finapi_client_secret,
                "finapi_user_id": src.finapi_user_id,
                "finapi_user_password": src_sudo.finapi_user_password,
                "finapi_refresh_token": src_sudo.finapi_refresh_token,
            }
        )
        return provider

    def _get_or_create_provider_for_journal(self, journal):
        """Return the journal's finAPI provider, creating it if needed.

        Normally ``account.journal._update_providers`` (OCA base module)
        auto-creates and links the provider synchronously during journal
        creation. This fallback removes the hard dependency on that
        behaviour staying unchanged.
        """
        provider = journal.online_bank_statement_provider_id
        if not provider:
            provider = self.env["online.bank.statement.provider"].create(
                {
                    "journal_id": journal.id,
                    "service": "finapi",
                }
            )
            journal.online_bank_statement_provider_id = provider
        return provider

    # -------------------------------------------------------------------
    # Helpers
    # -------------------------------------------------------------------
    def _populate_accounts(self, interface, token, bank_connection_id):
        self.account_ids.unlink()
        accounts = interface.list_accounts(token, bank_connection_id)
        rows = [
            (
                0,
                0,
                {
                    "finapi_account_id": str(a.get("id") or ""),
                    "iban": a.get("iban") or a.get("accountNumber") or "",
                    "name": a.get("accountHolderName") or a.get("accountName") or "",
                    "account_type": a.get("accountTypeName")
                    or a.get("accountType")
                    or "",
                    "balance": a.get("balance") or 0.0,
                    "currency": a.get("currency") or "",
                },
            )
            for a in accounts
        ]
        self.write({"account_ids": rows})

    def _reopen(self):
        return {
            "type": "ir.actions.act_window",
            "res_model": self._name,
            "res_id": self.id,
            "view_mode": "form",
            "target": "new",
        }


class FinapiWebformWizardAccount(models.TransientModel):
    _name = "finapi.webform.wizard.account"
    _description = "finAPI account choice for the wizard"

    wizard_id = fields.Many2one(
        "finapi.webform.wizard",
        required=True,
        ondelete="cascade",
    )
    finapi_account_id = fields.Char(required=True)
    bank_connection_id = fields.Char(
        help="finAPI bank connection this account belongs to.",
    )
    iban = fields.Char()
    name = fields.Char()
    account_type = fields.Char()
    balance = fields.Float()
    currency = fields.Char()

    def name_get(self):
        return [
            (
                rec.id,
                f"{rec.iban or rec.finapi_account_id} — {rec.name or ''}"
                f" ({rec.account_type or ''})",
            )
            for rec in self
        ]
