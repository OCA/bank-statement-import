# Copyright 2024 Binhex - Adasat Torres de León.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
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
    plaid_access_token = fields.Char()
    plaid_host = fields.Selection(
        [
            ("sandbox", "Sandbox"),
            ("production", "Production"),
        ],
        default="sandbox",
    )

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "plaid":
            return super()._obtain_statement_data(date_since, date_until)
        lines = self._plaid_retrieve_data(date_since, date_until)
        self._plaid_replace_settled_pending_lines(lines)
        return lines, {}

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
        raise UserError(_("Country code not found for the bank or the company..."))

    def _verify_lang(self, lang):
        if lang not in AVAILABLE_LANGS:
            return "en"
        return lang

    def action_sync_with_plaid(self):
        self.ensure_one()
        plaid_interface = self.env["plaid.interface"]
        args = [self.username, self.password, self.plaid_host]
        client = plaid_interface._client(*args)
        lang = (
            self.env["res.lang"]._lang_get(self.env.lang or self.env.user.lang).iso_code
        )
        company_name = self.env.company.name

        link_token = plaid_interface._link(
            client=client,
            language=self._verify_lang(lang),
            country_code=self._country_code(),
            company_name=company_name,
            products=["transactions"],
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

    def _plaid_retrieve_data(self, date_since, date_until):
        if not self.plaid_access_token:
            raise UserError(
                _(
                    "Please link your Plaid account first by "
                    "clicking on 'Sync with Plaid'."
                )
            )
        plaid_interface = self.env["plaid.interface"]
        args = [self.username, self.password, self.plaid_host]
        client = plaid_interface._client(*args)
        transactions = plaid_interface._get_transactions(
            client, self.plaid_access_token, date_since, date_until
        )
        return self._prepare_vals_for_statement(transactions)

    @api.model
    def plaid_create_access_token(self, public_token, active_id):
        provider = self.browse(active_id)
        plaid_interface = self.env["plaid.interface"]
        client = plaid_interface._client(
            provider.username, provider.password, provider.plaid_host
        )
        args = [client, public_token]
        provider.plaid_access_token = plaid_interface._login(*args)
        if provider.plaid_access_token:
            return True
        return False

    def _prepare_vals_for_statement(self, transactions):
        return [
            {
                "date": transaction["date"],
                "ref": transaction["name"],
                "payment_ref": transaction["name"],
                "unique_import_id": transaction["transaction_id"],
                "amount": float(transaction["amount"]) * -1.00,
                "raw_data": transaction,
                "plaid_pending_transaction_id": transaction.get(
                    "pending_transaction_id"
                ),
            }
            for transaction in transactions
        ]

    def _plaid_replace_settled_pending_lines(self, lines):
        """Delete previously imported pending lines superseded by settled ones.

        When a Plaid transaction settles it receives a new
        ``transaction_id``; the old pending ID is stored in
        ``pending_transaction_id``.  If the pending version was already
        imported, we remove it so the settled version can take its place.
        Reconciled lines are never touched.
        """
        BankStLine = self.env["account.bank.statement.line"]
        journal = self.journal_id
        account_number = self.account_number
        for line_vals in lines:
            pending_tid = line_vals.pop("plaid_pending_transaction_id", None)
            if not pending_tid:
                continue
            # Reconstruct the unique_import_id as stored by the base
            # module (which prepends account/journal info).
            lookup = {"unique_import_id": pending_tid}
            journal._statement_line_import_update_unique_import_id(
                lookup, account_number
            )
            existing = BankStLine.sudo().search(
                [("unique_import_id", "=", lookup["unique_import_id"])],
                limit=1,
            )
            if existing and not existing.is_reconciled:
                existing.move_id.button_draft()
                existing.move_id.unlink()
