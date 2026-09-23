# Copyright 2025 Wealthreader
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import hashlib
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

WEALTHREADER_API_BASE = "https://api.wealthreader.com"
WEALTHREADER_REQUEST_TIMEOUT = 120


class OnlineBankStatementProviderWealthreader(models.Model):
    _inherit = "online.bank.statement.provider"

    wealthreader_entity_code = fields.Char(
        string="Entity Code",
        help=(
            "The bank entity code as listed at "
            "https://www.wealthreader.com/supported-entities/ "
            "(e.g. 'caixabank', 'santander', 'bbva')."
        ),
    )
    wealthreader_token = fields.Char(
        string="Credential Token",
        help=(
            "Tokenized credential returned by Wealthreader after the first "
            "successful login. Using a token avoids sending raw credentials "
            "on every request. Leave empty on first connection; it will be "
            "populated automatically."
        ),
    )
    wealthreader_bank_password = fields.Char(
        string="Bank Password",
        help=(
            "Online banking password used together with the bank username. "
            "Only needed until the credential is tokenized; afterwards the "
            "token is used instead."
        ),
    )
    wealthreader_account_uuid = fields.Char(
        string="Account UUID",
        help=(
            "UUID of the specific bank account to import transactions from. "
            "When multiple accounts are returned by the entity, this field "
            "identifies which one maps to this Odoo journal. It is populated "
            "automatically after the first successful synchronization."
        ),
        readonly=True,
    )
    wealthreader_account_code = fields.Char(
        string="Account Code (IBAN)",
        help=(
            "IBAN or account code returned by Wealthreader. Displayed for "
            "informational purposes and used to match the correct account "
            "when the entity returns multiple accounts."
        ),
        readonly=True,
    )
    wealthreader_date_field = fields.Selection(
        selection=[
            ("operation_date", "Operation Date"),
            ("value_date", "Value Date"),
        ],
        string="Transaction Date Type",
        default="value_date",
        help=(
            "Choose which date to use for each imported transaction line. "
            "'Operation Date' is when the bank processed the operation; "
            "'Value Date' is when funds were effectively available."
        ),
    )

    # ------------------------------------------------------------------
    # Service registration
    # ------------------------------------------------------------------

    @api.model
    def _get_available_services(self):
        """Register Wealthreader as an available online banking service."""
        services = super()._get_available_services()
        services.append(("wealthreader", "Wealthreader"))
        return services

    # ------------------------------------------------------------------
    # Main data retrieval entry point
    # ------------------------------------------------------------------

    def _obtain_statement_data(self, date_since, date_until):
        """Retrieve bank statement data from the Wealthreader API.

        This method is called by the base framework to fetch transactions
        for the given date range.

        Args:
            date_since (datetime): Start of the period (inclusive).
            date_until (datetime): End of the period (inclusive).

        Returns:
            tuple: (lines, statement_values) where *lines* is a list of
                dicts ready for ``account.bank.statement.line`` creation and
                *statement_values* is a dict with ``balance_start`` and
                ``balance_end_real``.
        """
        if self.service != "wealthreader":
            return super()._obtain_statement_data(date_since, date_until)
        return self._wealthreader_obtain_statement_data(date_since, date_until)

    # ------------------------------------------------------------------
    # Wealthreader-specific logic
    # ------------------------------------------------------------------

    def _wealthreader_obtain_statement_data(self, date_since, date_until):
        """Fetch and parse Wealthreader account transactions.

        Calls the ``POST /entities/`` endpoint with ``product_types=accounts``
        and the configured date range, then converts the response into the
        format expected by the base statement import framework.
        """
        payload = self._wealthreader_fetch_entity_data(date_since, date_until)

        accounts = payload.get("accounts", [])
        if not accounts:
            _logger.info(
                "Wealthreader returned no accounts for entity '%s'.",
                self.wealthreader_entity_code,
            )
            return [], {}

        account = self._wealthreader_select_account(accounts)

        # Persist the account UUID and IBAN for future reference
        vals_to_write = {}
        account_uuid = account.get("uuid")
        account_code = account.get("code", "")
        if account_uuid and account_uuid != self.wealthreader_account_uuid:
            vals_to_write["wealthreader_account_uuid"] = account_uuid
        if account_code and account_code != self.wealthreader_account_code:
            vals_to_write["wealthreader_account_code"] = account_code
        if vals_to_write:
            self.write(vals_to_write)

        # Parse transactions
        lines = self._wealthreader_parse_transactions(
            account.get("transactions", []),
        )

        # Build statement balances
        balances = account.get("balances", {})
        statement_values = {}
        if balances.get("current") is not None:
            statement_values["balance_end_real"] = balances["current"]

        return lines, statement_values

    def _wealthreader_fetch_entity_data(self, date_since, date_until):
        """Call POST /entities/ and return the payload dict.

        On the first successful request, if Wealthreader returns a token in
        ``statistics``, it is saved so that subsequent calls no longer need
        raw credentials.
        """
        api_key = self.password
        if not api_key:
            raise UserError(
                _(
                    "Please set the Wealthreader API Key in the provider "
                    "configuration (Secret Key field)."
                )
            )
        if not self.wealthreader_entity_code:
            raise UserError(
                _(
                    "Please set the Entity Code in the provider "
                    "configuration (e.g. 'caixabank', 'santander')."
                )
            )

        data = {
            "api_key": api_key,
            "code": self.wealthreader_entity_code,
            "product_types": "accounts",
            "date_from": date_since.strftime("%Y-%m-%d"),
            "date_to": date_until.strftime("%Y-%m-%d"),
        }

        # Prefer token-based authentication if a token is stored
        if self.wealthreader_token:
            data["token"] = self.wealthreader_token
        elif self.username:
            data["user"] = self.username
            if self.wealthreader_bank_password:
                data["password"] = self.wealthreader_bank_password

        response = self._wealthreader_request("/entities/", data)

        # Persist token from first successful tokenized call
        statistics = response.get("statistics", {})
        new_token = statistics.get("token")
        if new_token and new_token != self.wealthreader_token:
            self.write({"wealthreader_token": new_token})

        payload_raw = response.get("payload")
        if not payload_raw:
            return {}

        # payload can be a list (array of entities) — take the first element
        if isinstance(payload_raw, list):
            if not payload_raw:
                return {}
            return payload_raw[0] if isinstance(payload_raw[0], dict) else {}

        return payload_raw if isinstance(payload_raw, dict) else {}

    def _wealthreader_select_account(self, accounts):
        """Pick the correct account from the entity response.

        If ``wealthreader_account_uuid`` is already set, use it.  Otherwise
        try to match by IBAN against the journal's bank account number.  If
        there is still no match and only one account is returned, use it
        directly.  Raise an error when ambiguity cannot be resolved.
        """
        if self.wealthreader_account_uuid:
            for acc in accounts:
                if acc.get("uuid") == self.wealthreader_account_uuid:
                    return acc

        # Try matching by IBAN
        journal_iban = (self.account_number or "").replace(" ", "").upper()
        if journal_iban:
            for acc in accounts:
                acc_code = (acc.get("code") or "").replace(" ", "").upper()
                if acc_code and acc_code == journal_iban:
                    return acc

        if len(accounts) == 1:
            return accounts[0]

        account_descriptions = ", ".join(
            f"{a.get('name', '?')} ({a.get('code', '?')})" for a in accounts
        )
        raise UserError(
            _(
                "Wealthreader returned multiple accounts and the correct "
                "one could not be determined automatically. Please ensure "
                "the journal's bank account number (IBAN) matches one of "
                "the following accounts: %s",
                account_descriptions,
            )
        )

    # ------------------------------------------------------------------
    # Transaction parsing
    # ------------------------------------------------------------------

    def _wealthreader_parse_transactions(self, transactions):
        """Convert Wealthreader transaction dicts to statement line dicts."""
        lines = []
        for tr in transactions:
            line = self._wealthreader_transaction_to_line(tr)
            if line:
                lines.append(line)
        return lines

    def _wealthreader_transaction_to_line(self, tr):
        """Map a single Wealthreader transaction to a statement line dict.

        The expected Wealthreader transaction structure (from API spec)::

            {
                "uuid": "...",
                "operation_date": "YYYY-MM-DD",
                "value_date": "YYYY-MM-DD",
                "amount": 123.45,
                "balance": 1000.00,
                "description": "Payment ...",
                "categorization": {"type": "..."},
                "transfer_details": {
                    "concept": "...",
                    "sender_receiver": "...",
                    "account_number": "..."
                }
            }
        """
        amount = tr.get("amount")
        if amount is None:
            return None

        date_field = self.wealthreader_date_field or "value_date"
        raw_date = (
            tr.get(date_field) or tr.get("value_date") or tr.get("operation_date")
        )
        if not raw_date:
            return None

        # Build the line dict
        line = {
            "date": raw_date,
            "amount": amount,
            "payment_ref": self._wealthreader_get_payment_ref(tr),
            "unique_import_id": self._wealthreader_get_unique_id(tr),
        }

        # Partner information from transfer_details
        transfer = tr.get("transfer_details") or {}
        partner_name = transfer.get("sender_receiver")
        if partner_name:
            line["partner_name"] = partner_name
        partner_account = transfer.get("account_number")
        if partner_account:
            line["account_number"] = partner_account

        # Narration / note with extra details
        note = self._wealthreader_build_note(tr)
        if note:
            line["narration"] = note

        return line

    def _wealthreader_get_payment_ref(self, tr):
        """Extract the best available payment reference from a transaction."""
        transfer = tr.get("transfer_details") or {}
        concept = transfer.get("concept")
        if concept:
            return concept
        return tr.get("description", "")

    def _wealthreader_get_unique_id(self, tr):
        """Build a unique import ID from the transaction UUID.

        Falls back to a combination of date + amount + description when the
        UUID is not available.
        """
        uuid = tr.get("uuid")
        if uuid:
            return f"WR-{uuid}"
        # Fallback — deterministic but less reliable
        date_str = tr.get("value_date") or tr.get("operation_date") or ""
        amount = tr.get("amount", 0)
        desc = tr.get("description", "")
        desc_digest = hashlib.sha1(desc.encode("utf-8")).hexdigest()[:12]
        return f"WR-{date_str}-{amount}-{desc_digest}"

    def _wealthreader_build_note(self, tr):
        """Compose a detailed note from transaction metadata."""
        parts = []

        description = tr.get("description")
        if description:
            parts.append(description)

        transfer = tr.get("transfer_details") or {}
        concept = transfer.get("concept")
        if concept and concept != description:
            parts.append(_("Concept: %s", concept))
        sender_receiver = transfer.get("sender_receiver")
        if sender_receiver:
            parts.append(_("Counterparty: %s", sender_receiver))
        account_number = transfer.get("account_number")
        if account_number:
            parts.append(_("Account: %s", account_number))

        categorization = tr.get("categorization") or {}
        cat_type = categorization.get("type")
        if cat_type:
            parts.append(_("Category: %s", cat_type))

        op_date = tr.get("operation_date")
        val_date = tr.get("value_date")
        if op_date and val_date and op_date != val_date:
            parts.append(
                _(
                    "Operation date: %(op_date)s / Value date: %(val_date)s",
                    op_date=op_date,
                    val_date=val_date,
                )
            )

        return "\n".join(parts) if parts else ""

    # ------------------------------------------------------------------
    # HTTP helpers
    # ------------------------------------------------------------------

    def _wealthreader_request(self, endpoint, data):
        """Send a POST request to the Wealthreader API.

        Args:
            endpoint (str): API path (e.g. ``/entities/``).
            data (dict): POST body (sent as form-encoded).

        Returns:
            dict: Parsed JSON response.

        Raises:
            UserError: On HTTP or API-level errors.
        """
        url = f"{self.api_base or WEALTHREADER_API_BASE}{endpoint}"
        _logger.debug(
            "Wealthreader request: POST %s (entity=%s)",
            url,
            data.get("code", "?"),
        )
        try:
            resp = requests.post(url, data=data, timeout=WEALTHREADER_REQUEST_TIMEOUT)
        except requests.exceptions.Timeout as err:
            raise UserError(
                _(
                    "The request to Wealthreader timed out. The bank may "
                    "be temporarily slow. Please try again later."
                )
            ) from err
        except requests.exceptions.ConnectionError as err:
            raise UserError(
                _(
                    "Could not connect to Wealthreader. Please check your "
                    "internet connection and try again."
                )
            ) from err

        try:
            result = resp.json()
        except ValueError as err:
            _logger.error(
                "Wealthreader returned non-JSON response (HTTP %s): %s",
                resp.status_code,
                resp.text[:500],
            )
            raise UserError(
                _(
                    "Unexpected response from Wealthreader (HTTP %s). "
                    "Please try again later or contact support.",
                    resp.status_code,
                )
            ) from err

        if not result.get("success", True):
            error = result.get("error", {})
            error_code = error.get("code", "?")
            error_msg = error.get("message", _("Unknown error"))
            _logger.warning("Wealthreader API error %s: %s", error_code, error_msg)
            raise UserError(
                _(
                    "Wealthreader error (code %(code)s): %(message)s",
                    code=error_code,
                    message=error_msg,
                )
            )

        return result

    # ------------------------------------------------------------------
    # Action: Fetch available entities (for user guidance)
    # ------------------------------------------------------------------

    def action_wealthreader_test_connection(self):
        """Test the connection by fetching entity data for today.

        Useful for verifying credentials and entity code before scheduling
        automatic pulls.
        """
        self.ensure_one()
        now = fields.Datetime.now()
        try:
            payload = self._wealthreader_fetch_entity_data(now, now)
        except UserError as exc:
            raise UserError(_("Connection test failed: %s", exc.args[0])) from exc

        accounts = payload.get("accounts", [])
        if accounts:
            account_lines = []
            for a in accounts:
                account_lines.append(
                    "  - {} ({})".format(
                        a.get("name", "?"),
                        a.get("code", "?"),
                    )
                )
            account_info = "\n".join(account_lines)
            message = _(
                "Connection successful! Found %(count)d account(s):\n%(accounts)s",
                count=len(accounts),
                accounts=account_info,
            )
        else:
            message = _(
                "Connection successful but no accounts were returned. "
                "Please verify the entity code and credentials."
            )

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("Wealthreader"),
                "message": message,
                "sticky": False,
                "type": "info",
            },
        }
