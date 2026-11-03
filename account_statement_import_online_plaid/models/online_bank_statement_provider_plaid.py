# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
from datetime import datetime, time, timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError

AVAILABLE_LANGS = [
    "da",
    "nl",
    "en",
    "et",
    "fr",
    "de",
    "hi",
    "it",
    "lv",
    "lt",
    "no",
    "pl",
    "pt",
    "ro",
    "es",
    "sv",
    "vi",
]


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    plaid_access_token = fields.Char(copy=False, groups="base.group_system")
    plaid_host = fields.Selection(
        [
            ("sandbox", "Sandbox"),
            ("production", "Production"),
        ],
        default="sandbox",
    )
    plaid_link_provider_id = fields.Many2one(
        comodel_name="online.bank.statement.provider",
        string="Use Plaid Login Of",
        domain="[('service', '=', 'plaid'), ('id', '!=', id),"
        " ('plaid_link_provider_id', '=', False)]",
        ondelete="restrict",
        help="Share the bank login of another provider, for a second account at "
        "the same bank, such as a credit card next to a checking account. Plaid "
        "bills per login, and the bank is only linked once.",
    )
    plaid_linked = fields.Boolean(
        string="Linked to Plaid",
        compute="_compute_plaid_linked",
    )
    plaid_account_id = fields.Char(
        string="Plaid Account ID",
        copy=False,
        help="The account at the bank whose transactions are imported. One "
        "login can hold several accounts.",
    )
    plaid_account_name = fields.Char(string="Plaid Account", copy=False)
    plaid_lookback_days = fields.Integer(
        string="Plaid Lookback (days)",
        default=14,
        help="Scheduled pulls also ask Plaid for this many days before the last "
        "pull. Banks post many transactions a few days after their date, and "
        "those would be missed otherwise. Lines already imported are skipped.",
    )

    @api.depends(
        "plaid_access_token",
        "plaid_link_provider_id",
        "plaid_link_provider_id.plaid_access_token",
    )
    def _compute_plaid_linked(self):
        for provider in self:
            provider.plaid_linked = bool(
                provider._plaid_source().sudo().plaid_access_token
            )

    def _plaid_source(self):
        """Return the provider holding the Plaid login and credentials."""
        self.ensure_one()
        return self.plaid_link_provider_id or self

    def _plaid_client(self):
        source = self._plaid_source().sudo()
        return self.env["plaid.interface"]._client(
            source.username, source.password, source.plaid_host
        )

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "plaid":
            return super()._obtain_statement_data(date_since, date_until)
        return self._plaid_retrieve_data(date_since, date_until), {}

    def _pull(self, date_since, date_until):
        # The framework asks for one statement period at a time (a day by
        # default). Fetch the whole range from Plaid once instead, which keeps
        # long pulls under Plaid's rate limits.
        lookback = self.env.context.get("scheduled") or self.env.context.get(
            "plaid_lookback"
        )
        data = []
        for provider in self:
            since = date_since
            if (
                provider.service == "plaid"
                and lookback
                and provider.plaid_lookback_days
            ):
                since = min(
                    date_since,
                    date_until - timedelta(days=provider.plaid_lookback_days),
                )
            data += (
                super(
                    OnlineBankStatementProvider,
                    provider.with_context(plaid_cache={}, plaid_pull_until=date_until),
                )._pull(since, date_until)
                or []
            )
        return data

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("plaid", "Plaid.com"),
        ]

    def _country_code(self):
        if self.journal_id.bank_id and self.journal_id.bank_id.country:
            return self.journal_id.bank_id.country.code
        if self.journal_id.company_id.country_id:
            return self.journal_id.company_id.country_id.code
        raise UserError(
            self.env._("Country code not found for the bank or the company...")
        )

    def _verify_lang(self, lang):
        if lang not in AVAILABLE_LANGS:
            return "en"
        return lang

    def action_sync_with_plaid(self):
        """Open Plaid Link to connect the bank, or to repair an expired login."""
        self.ensure_one()
        if self.plaid_link_provider_id:
            raise UserError(
                self.env._(
                    "This provider uses the Plaid login of %(provider)s. "
                    "Link or reconnect the bank from there.",
                    provider=self.plaid_link_provider_id.display_name,
                )
            )
        self.check_access("write")
        lang = (
            self.env["res.lang"]._lang_get(self.env.lang or self.env.user.lang).iso_code
        )
        link_token = self.env["plaid.interface"]._link(
            client=self._plaid_client(),
            language=self._verify_lang(lang),
            country_code=self._country_code(),
            company_name=self.env.company.name,
            products=["transactions"],
            access_token=self.sudo().plaid_access_token,
        )
        return {
            "type": "ir.actions.client",
            "tag": "plaid_login",
            "params": {
                "call_model": "online.bank.statement.provider",
                "call_method": "plaid_create_access_token",
                "token": link_token,
                "object_id": self.id,
            },
            "target": "new",
        }

    @api.model
    def plaid_create_access_token(self, public_token, active_id):
        """Store the login from Plaid Link, then choose the account.

        In update mode Link keeps the existing login, so there is no new
        token to exchange.
        """
        provider = self.browse(active_id)
        provider.check_access("write")
        if public_token and not provider.sudo().plaid_access_token:
            access_token = self.env["plaid.interface"]._login(
                provider._plaid_client(), public_token
            )
            provider.sudo().plaid_access_token = access_token
        if provider.plaid_account_id:
            return False
        return provider.action_plaid_select_account()

    def action_plaid_unlink(self):
        """Remove the bank login at Plaid and forget it here."""
        self.ensure_one()
        self.check_access("write")
        if self.plaid_link_provider_id:
            self.write(
                {
                    "plaid_link_provider_id": False,
                    "plaid_account_id": False,
                    "plaid_account_name": False,
                }
            )
            return
        sharing = self.search([("plaid_link_provider_id", "=", self.id)])
        if sharing:
            raise UserError(
                self.env._(
                    "%(providers)s share this bank login. Unlink them first.",
                    providers=", ".join(sharing.mapped("display_name")),
                )
            )
        access_token = self.sudo().plaid_access_token
        if access_token:
            self.env["plaid.interface"]._remove(self._plaid_client(), access_token)
        self.sudo().write(
            {
                "plaid_access_token": False,
                "plaid_account_id": False,
                "plaid_account_name": False,
            }
        )

    def action_plaid_select_account(self):
        """Choose the account to import. A login with one account selects it
        directly; otherwise a wizard lists the accounts."""
        self.ensure_one()
        source = self._plaid_source().sudo()
        if not source.plaid_access_token:
            raise UserError(
                self.env._("Link the bank with Plaid first: click 'Link with Plaid'.")
            )
        accounts = self.env["plaid.interface"]._get_accounts(
            self._plaid_client(), source.plaid_access_token
        )
        if len(accounts) == 1:
            self._plaid_set_account(accounts[0])
            return False
        wizard = self.env["plaid.account.select"].create(
            {
                "provider_id": self.id,
                "line_ids": [
                    (
                        0,
                        0,
                        {
                            "plaid_account_id": account["account_id"],
                            "name": self._plaid_account_label(account),
                        },
                    )
                    for account in accounts
                ],
            }
        )
        return {
            "type": "ir.actions.act_window",
            "name": self.env._("Choose the Bank Account"),
            "res_model": "plaid.account.select",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    @api.model
    def _plaid_account_label(self, account):
        label = account.get("official_name") or account.get("name") or ""
        if account.get("mask"):
            label = f"{label} ••{account['mask']}"
        return label

    def _plaid_set_account(self, account):
        self.write(
            {
                "plaid_account_id": account["account_id"],
                "plaid_account_name": self._plaid_account_label(account),
            }
        )

    def _plaid_retrieve_data(self, date_since, date_until):
        source = self._plaid_source().sudo()
        if not source.plaid_access_token:
            raise UserError(
                self.env._(
                    "Please link your Plaid account first by "
                    "clicking on 'Link with Plaid'."
                )
            )
        if not self.plaid_account_id:
            raise UserError(
                self.env._(
                    "Choose which bank account to import: click 'Choose Account'."
                )
            )
        cache = self.env.context.get("plaid_cache")
        if cache is not None and self.id in cache:
            transactions = cache[self.id]
        else:
            # Plaid works in dates. Periods start at midnight in the provider's
            # timezone, and their end is exclusive.
            start = self._utc_to_provider_tz(date_since).date()
            end = self._plaid_last_period_end(date_until) - timedelta(seconds=1)
            end = min(end.date(), fields.Date.context_today(self))
            transactions = self.env["plaid.interface"]._get_transactions(
                self._plaid_client(),
                source.plaid_access_token,
                start,
                max(start, end),
                account_ids=[self.plaid_account_id],
            )
            if cache is not None:
                cache[self.id] = transactions
        return self._prepare_vals_for_statement(transactions)

    def _plaid_last_period_end(self, date_until):
        """End of the last statement period of this pull, in the provider's
        timezone, the way the framework's _pull() steps through periods."""
        local_until = self._utc_to_provider_tz(date_until)
        pull_until = self.env.context.get("plaid_pull_until")
        if pull_until:
            local_pull_until = self._utc_to_provider_tz(pull_until)
            period_start = self._get_statement_date_since(local_pull_until)
            if period_start < local_pull_until:
                period_start += self._get_statement_date_step()
            local_until = max(local_until, period_start)
        return local_until

    def _prepare_vals_for_statement(self, transactions):
        # Pending transactions are left out: they get a new ID once posted,
        # and would be imported twice.
        return [
            {
                "date": self._plaid_line_date(transaction["date"]),
                "ref": transaction["name"],
                "payment_ref": transaction["name"],
                "partner_name": transaction.get("merchant_name") or False,
                "unique_import_id": transaction["transaction_id"],
                # Plaid amounts are positive for money out, on bank and credit
                # card accounts alike.
                "amount": float(transaction["amount"]) * -1.00,
                "raw_data": json.dumps(transaction, default=str),
            }
            for transaction in transactions
            if not transaction.get("pending")
        ]

    def _plaid_line_date(self, date):
        """Midnight of the transaction date in the provider's timezone, as
        naive UTC, so the line lands on the same date in the statement."""
        if isinstance(date, str):
            date = fields.Date.from_string(date)
        return self._provider_tz_to_utc(datetime.combine(date, time.min))
