# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone

from odoo import _, api, fields, models
from odoo.exceptions import RedirectWarning, UserError

from .finapi_interface import (
    FinapiApiError,
    FinapiAuthError,
    FinapiInterface,
    FinapiWebFormRequiredError,
)

_logger = logging.getLogger(__name__)


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    # PSD2 allows at most four customer-not-present AIS accesses per day. With
    # an hourly pull cron we therefore throttle the bank-connection refresh to
    # at most once every six hours (= four per day). The read
    # (``GET /transactions``) itself stays unthrottled.
    _finapi_min_data_update_interval_hours = 6
    # Web Form 2.0 ``backgroundUpdate`` is asynchronous: we poll the task until
    # it reaches a terminal status. Within a valid recurring consent it
    # finishes in a few seconds; cap the wait so a stuck or SCA-required task
    # never blocks the pull.
    _finapi_background_update_poll_seconds = 3
    _finapi_background_update_max_wait_seconds = 90

    # ---------------------------------------------------------------
    # Provider-specific fields
    # ---------------------------------------------------------------
    finapi_environment = fields.Selection(
        [
            ("sandbox", "Sandbox"),
            ("live", "Live"),
        ],
        string="finAPI Environment",
        default="sandbox",
        required=True,
        help="Select whether to connect to the finAPI sandbox (testing) "
        "or the live production system. Switching this updates the "
        "Base URL and Web Form URL to the corresponding finAPI endpoints. "
        "You can still override the URLs manually below for advanced setups.",
    )
    finapi_base_url = fields.Char(
        string="finAPI Base URL",
        help="Access API base URL. Auto-filled from the selected "
        "environment; override only for custom endpoints (e.g. a proxy).",
    )
    finapi_webform_base_url = fields.Char(
        string="finAPI Web Form URL",
        help="Web Form 2.0 API base URL. Auto-filled from the selected "
        "environment; override only for custom endpoints.",
    )
    finapi_client_id = fields.Char(string="finAPI Client ID")
    finapi_client_secret = fields.Char(
        string="finAPI Client Secret",
        groups="base.group_system",
    )
    finapi_user_id = fields.Char(
        string="finAPI User ID",
        readonly=True,
        copy=False,
        help="Auto-generated when you click 'Create finAPI user'.",
    )
    finapi_user_password = fields.Char(
        string="finAPI User Password",
        readonly=True,
        copy=False,
        groups="base.group_system",
    )
    finapi_refresh_token = fields.Char(
        string="finAPI Refresh Token",
        readonly=True,
        copy=False,
        groups="base.group_system",
    )
    # finAPI account / bank-connection IDs are int64 in the finAPI API and can
    # exceed the 2^31 range of an Odoo Integer (int4) in the live platform, so
    # they are stored as Char and cast to int only at the API boundary.
    finapi_bank_connection_id = fields.Char(
        string="finAPI Bank Connection ID",
        readonly=True,
        copy=False,
    )
    finapi_account_id = fields.Char(
        string="finAPI Account ID",
        readonly=True,
        copy=False,
        help="The finAPI account whose transactions will be imported by this "
        "provider. One Odoo bank account = one finAPI account.",
    )
    finapi_consent_expires_at = fields.Datetime(
        string="PSD2 Consent expires at",
        readonly=True,
        copy=False,
        help="finAPI consents are valid for 90 days. After that a Web Form "
        "Update is required.",
    )
    finapi_last_webform_id = fields.Char(
        string="Last Web Form ID",
        readonly=True,
        copy=False,
    )
    finapi_consent_alert_expiry = fields.Datetime(
        string="Consent expiry already alerted",
        readonly=True,
        copy=False,
        help="Internal: consent expiry datetime for which a warning email "
        "has already been sent. Prevents the daily cron from sending "
        "duplicate alerts.",
    )
    finapi_refresh_mode = fields.Selection(
        [
            ("background", "Web Form background update (default)"),
            ("direct", "Direct update (licensed TPP only)"),
            ("none", "No refresh (rely on finAPI batch update)"),
        ],
        string="finAPI Data Refresh",
        default="background",
        required=True,
        help="How the scheduled pull fetches fresh bookings before reading "
        "them (``GET /transactions`` only returns data finAPI already "
        "stored):\n"
        "- Web Form background update: triggers finAPI's "
        "``POST /tasks/backgroundUpdate``. Within a valid recurring consent "
        "it completes without user interaction. Works for standard "
        "(finAPI-licensed / Web Form) mandators. Recommended.\n"
        "- Direct update: customer-not-present "
        "``POST /bankConnections/update`` — only allowed if your mandator "
        "holds its own PSD2/TPP license (finAPI rejects it otherwise).\n"
        "- No refresh: only read what finAPI already has (use when finAPI's "
        "Automatic Batch Update keeps the connection fresh server-side).",
    )
    finapi_banking_interface = fields.Char(
        string="finAPI Banking Interface",
        readonly=True,
        copy=False,
        help="Interface that carries the PSD2 consent (e.g. XS2A). Used to "
        "target the direct data refresh of licensed mandators. Populated by "
        "'Check connection'.",
    )
    finapi_last_data_update = fields.Datetime(
        string="Last finAPI Data Refresh",
        readonly=True,
        copy=False,
        help="When a refresh of this bank connection was last attempted. "
        "Failed attempts count too: they have already asked finAPI to "
        "contact the bank. Used to stay within the PSD2 limit of four "
        "customer-not-present accesses per day.",
    )
    finapi_lookback_days = fields.Integer(
        string="Re-check last N days",
        default=7,
        help="On each *scheduled* pull, also re-fetch the last N days of "
        "transactions. Banks frequently add a booking with a past booking "
        "date after our import cursor has already moved on (e.g. an evening "
        "transfer, or a weekend booking posted on Monday); without this they "
        "would never be imported. Already-imported lines are skipped via "
        "their unique import id, so re-fetching never creates duplicates. "
        "Manual syncs keep the date range you select. Set to 0 to disable.",
    )

    # ---------------------------------------------------------------
    # Register the service
    # ---------------------------------------------------------------
    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [("finapi", "finAPI")]

    # ---------------------------------------------------------------
    # Main hook called by the OCA framework
    # ---------------------------------------------------------------
    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "finapi":
            return super()._obtain_statement_data(date_since, date_until)
        return self._finapi_obtain_statement_data(date_since, date_until)

    def _pull(self, date_since, date_until):
        """Extend the *scheduled* pull window backwards by a lookback.

        The OCA framework only pulls ``[last_successful_run, next_run]``, so a
        transaction the bank books with a past booking date *after* our cursor
        has advanced (a late evening transfer, a weekend booking posted on
        Monday, a pending item that becomes booked, ...) is never re-fetched
        and silently goes missing. Re-fetching the last ``finapi_lookback_days``
        days on every scheduled run closes that gap; OCA dedupes by
        ``unique_import_id`` so it never creates duplicates.

        Manual pulls (no ``scheduled`` context) keep the user-selected range.
        """
        if not self.env.context.get("scheduled"):
            return super()._pull(date_since, date_until)
        result = []
        for provider in self:
            provider_since = date_since
            if (
                provider.service == "finapi"
                and provider.finapi_lookback_days
                and date_until
            ):
                lookback_start = date_until - timedelta(
                    days=provider.finapi_lookback_days
                )
                if not provider_since or lookback_start < provider_since:
                    provider_since = lookback_start
            result += (
                super(OnlineBankStatementProvider, provider)._pull(
                    provider_since, date_until
                )
                or []
            )
        return result

    # ===============================================================
    # finAPI implementation
    # ===============================================================

    @api.model
    def _finapi_get_environment_urls(self):
        """Return the Access API and Web Form host of each finAPI environment.

        finAPI runs a sandbox for development and testing and the live
        production system, each with its own Access API and Web Form host.
        Override to point an environment elsewhere, e.g. at a proxy.
        """
        return {
            "sandbox": {
                "base": "https://sandbox.finapi.io",
                "webform": "https://webform-sandbox.finapi.io",
            },
            "live": {
                "base": "https://live.finapi.io",
                "webform": "https://webform-live.finapi.io",
            },
        }

    @api.onchange("finapi_environment")
    def _onchange_finapi_environment(self):
        """Set Base URL and Web Form URL to the environment's defaults.

        Lets the user see and tweak the concrete URLs in the form. For
        programmatic creation (no onchange) the interface factory falls back
        to the same defaults when the URL fields are empty.
        """
        urls = self._finapi_get_environment_urls().get(self.finapi_environment)
        if urls:
            self.finapi_base_url = urls["base"]
            self.finapi_webform_base_url = urls["webform"]

    # ---------- Interface factory ----------------------------------
    def _finapi_get_interface(self):
        self.ensure_one()
        icp = self.env["ir.config_parameter"].sudo()
        all_urls = self._finapi_get_environment_urls()
        env_urls = all_urls.get(self.finapi_environment, all_urls["sandbox"])
        base_url = (
            self.finapi_base_url
            or env_urls["base"]
            or icp.get_param("finapi.base_url", "https://sandbox.finapi.io")
        )
        webform_base_url = (
            self.finapi_webform_base_url
            or env_urls["webform"]
            or icp.get_param(
                "finapi.webform_base_url", "https://webform-sandbox.finapi.io"
            )
        )
        # sudo: the secret is restricted to base.group_system, but regular
        # accounting users must be able to trigger statement pulls. The
        # value is only used for the API call, never exposed.
        client_secret = self.sudo().finapi_client_secret
        if not self.finapi_client_id or not client_secret:
            raise UserError(
                _("Please set finAPI Client ID and Secret on the provider first.")
            )
        return FinapiInterface(
            base_url=base_url,
            client_id=self.finapi_client_id,
            client_secret=client_secret,
            webform_base_url=webform_base_url,
        )

    # ---------- Token helpers --------------------------------------
    def _finapi_get_user_token(self, interface=None):
        """Return a valid user access_token, refreshing or re-logging-in
        transparently. Persists any new refresh_token."""
        self.ensure_one()
        if interface is None:
            # No interface supplied — create one and ensure its HTTP
            # session is closed deterministically after use.
            with self._finapi_get_interface() as interface:
                return self._finapi_get_user_token(interface)
        # sudo: password/refresh token are restricted to base.group_system,
        # but regular accounting users must be able to trigger pulls.
        self_sudo = self.sudo()
        if not self.finapi_user_id or not self_sudo.finapi_user_password:
            raise UserError(
                _("No finAPI user configured. Click 'Create finAPI user' first.")
            )

        # 1) Try refresh if we have a refresh_token
        refresh_token = self_sudo.finapi_refresh_token
        if refresh_token:
            try:
                payload = interface.refresh_user_token(refresh_token)
                self_sudo.write(
                    {
                        "finapi_refresh_token": payload.get(
                            "refresh_token", refresh_token
                        ),
                    }
                )
                return payload["access_token"]
            except (FinapiAuthError, FinapiApiError) as exc:
                _logger.info(
                    "finAPI refresh token invalid for provider %s — "
                    "falling back to password grant (%s).",
                    self.id,
                    exc,
                )

        # 2) Fall back to full password grant
        payload = interface.get_user_token(
            self.finapi_user_id,
            self_sudo.finapi_user_password,
        )
        self_sudo.write(
            {
                "finapi_refresh_token": payload.get("refresh_token"),
            }
        )
        return payload["access_token"]

    # ---------- Statement data -------------------------------------
    def _finapi_obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if not self.finapi_account_id:
            raise UserError(_("No finAPI account linked. Add a bank connection first."))
        # finAPI expects YYYY-MM-DD, inclusive. Work in dates, not datetimes.
        date_from = date_since.date() if hasattr(date_since, "date") else date_since
        date_to = date_until.date() if hasattr(date_until, "date") else date_until

        # ``GET /transactions`` only returns the data finAPI already holds, so
        # unless something refreshes the bank connection the pull keeps
        # returning the same (stale) set. Depending on ``finapi_refresh_mode``
        # we first trigger a refresh (Web Form background-update task by
        # default, or a direct update for licensed TPPs). The refresh is
        # best-effort and throttled: a failure (e.g. expired consent / SCA
        # required) must never abort the pull -- we still read whatever finAPI
        # has cached and the consent-expiry cron alerts the user.
        with self._finapi_get_interface() as interface:
            token = self._finapi_get_user_token(interface)
            if self.finapi_refresh_mode != "none":
                self._finapi_refresh_bank_data(interface, token)
            raw_transactions = interface.list_transactions(
                token,
                self.finapi_account_id,
                date_from,
                date_to,
            )
            lines = [self._finapi_transaction_to_line(tx) for tx in raw_transactions]

            # Balance snapshot — best effort, never fail the pull on it.
            # finAPI only exposes the *current* account balance, so apply it
            # only to the current statement period. Re-fetching the lookback
            # window must NOT overwrite a past statement's real end balance
            # with today's live balance.
            balances = {}
            if self._finapi_is_current_period(date_since):
                try:
                    account = interface.get_account(token, self.finapi_account_id)
                    balance_end = account.get("balance")
                    if balance_end is not None:
                        balances = {"balance_end_real": balance_end}
                except (FinapiAuthError, FinapiApiError) as exc:
                    _logger.info(
                        "finAPI balance fetch failed for account %s: %s",
                        self.finapi_account_id,
                        exc,
                    )

        return lines, balances

    def _finapi_is_current_period(self, date_since):
        """True when the statement period extends into the present/future.

        Used to decide whether the live account balance applies (only the
        most recent statement period gets the current balance).

        The period end is derived from ``date_since`` plus the statement step,
        exactly as the framework's ``_pull`` computes it, instead of trusting
        the ``date_until`` we are handed: sibling providers may alter it before
        delegating to ``super()``. account_statement_import_online_ofx caps it
        at today 00:00 for every provider, which would make the current period
        look finished and suppress the live balance on any database that also
        has that module installed.

        Args:
            date_since: Start of the statement period.
        """
        self.ensure_one()
        if not isinstance(date_since, datetime):
            return True
        period_end = date_since + self._get_statement_date_step()
        return period_end > fields.Datetime.now()

    # ---------- Bank data refresh ----------------------------------
    def _finapi_refresh_bank_data(self, interface, token, force=False):
        """Ask finAPI to fetch fresh data from the bank before reading it.

        The mechanism depends on ``finapi_refresh_mode``:

        - ``background`` (default): start a Web Form 2.0 ``backgroundUpdate``
          task and poll it. Within a valid recurring consent it completes
          without user interaction; works for standard (finAPI-licensed / Web
          Form) mandators.
        - ``direct``: customer-not-present ``POST /bankConnections/update`` --
          only allowed for mandators holding their own PSD2/TPP license.

        Throttled to ``_finapi_min_data_update_interval_hours`` to stay within the
        PSD2 limit of four such accesses per day. When called from the
        scheduled pull (``force=False``) a failure must never abort the pull:
        we log a warning and read whatever finAPI has cached. When triggered
        manually (``force=True``) the throttle is bypassed and errors are
        re-raised so the user gets immediate feedback.

        Args:
            interface: An open :class:`FinapiInterface`.
            token: A valid finAPI user access token.
            force: Bypass the throttle and surface API errors.
        """
        self.ensure_one()
        if not self.finapi_bank_connection_id:
            return
        if not force and not self._finapi_data_update_due():
            _logger.debug(
                "finAPI data refresh skipped for provider %s "
                "(last refresh %s, throttled to every %sh).",
                self.id,
                self.finapi_last_data_update,
                self._finapi_min_data_update_interval_hours,
            )
            return
        # Arm the throttle *before* the attempt, not after a successful one.
        # A refresh that fails (expired consent / SCA) has still asked finAPI
        # to contact the bank, so it counts against the PSD2 access budget.
        # More importantly, the OCA framework splits a pull into one statement
        # period per day and calls us once per period: if a failure left the
        # throttle unarmed, every period would retry, and each retry polls the
        # background-update task for up to _finapi_background_update_max_wait_seconds.
        # An expired consent is the regular PSD2 end state, so that would block
        # a cron worker for minutes on every run until someone renews it.
        self.sudo().write({"finapi_last_data_update": fields.Datetime.now()})
        try:
            if self.finapi_refresh_mode == "direct":
                interface.update_bank_connection(
                    token,
                    self.finapi_bank_connection_id,
                    banking_interface=self.finapi_banking_interface or "XS2A",
                )
            else:
                self._finapi_run_background_update(interface, token)
        except (FinapiAuthError, FinapiApiError) as exc:
            if force:
                raise
            _logger.warning(
                "finAPI data refresh failed for provider %s "
                "(bank connection %s): %s -- reading cached data only.",
                self.id,
                self.finapi_bank_connection_id,
                exc,
            )
            return
        # Keep consent expiry / banking interface fresh (best effort).
        try:
            bank_connection = interface.get_bank_connection(
                token, self.finapi_bank_connection_id
            )
            self._finapi_store_connection_meta(bank_connection)
        except (FinapiAuthError, FinapiApiError) as exc:
            _logger.info(
                "finAPI: could not refresh connection meta for provider %s: %s",
                self.id,
                exc,
            )

    def _finapi_run_background_update(self, interface, token):
        """Start a Web Form 2.0 ``backgroundUpdate`` task and wait for it.

        Polls the task until a terminal status. Raises :class:`FinapiApiError`
        if the task fails, needs an interactive Web Form (SCA), or does not
        finish within ``_finapi_background_update_max_wait_seconds`` -- the caller
        treats these as best-effort failures (read cached data).

        Args:
            interface: An open :class:`FinapiInterface`.
            token: A valid finAPI user access token.
        """
        self.ensure_one()
        task = interface.start_background_update(token, self.finapi_bank_connection_id)
        task_id = task.get("id")
        status = task.get("status")
        waited = 0
        while status not in (
            "COMPLETED",
            "COMPLETED_WITH_ERROR",
            "WEB_FORM_REQUIRED",
        ):
            if waited >= self._finapi_background_update_max_wait_seconds or not task_id:
                raise FinapiApiError(
                    _(
                        "finAPI background update did not finish in time "
                        "(status=%(status)s)."
                    )
                    % {"status": status or "UNKNOWN"}
                )
            time.sleep(self._finapi_background_update_poll_seconds)
            waited += self._finapi_background_update_poll_seconds
            task = interface.get_task(token, task_id)
            status = task.get("status")
        if status == "COMPLETED":
            return
        payload = task.get("payload") or {}
        if status == "WEB_FORM_REQUIRED":
            web_form = payload.get("webForm") or {}
            webform_url = web_form.get("url")
            raise FinapiWebFormRequiredError(
                _(
                    "finAPI requires an interactive Web Form to refresh this "
                    "connection (SCA / consent renewal). Open: %(url)s"
                )
                % {"url": webform_url or _("see 'Renew consent')")},
                webform_url=webform_url,
            )
        # COMPLETED_WITH_ERROR
        raise FinapiApiError(
            _("finAPI background update failed: %(code)s %(msg)s")
            % {
                "code": payload.get("errorCode") or "",
                "msg": payload.get("errorMessage") or "",
            }
        )

    def _finapi_data_update_due(self):
        """Return True when the throttle window since the last refresh passed."""
        self.ensure_one()
        last = self.finapi_last_data_update
        if not last:
            return True
        next_due = fields.Datetime.add(
            last, hours=self._finapi_min_data_update_interval_hours
        )
        return fields.Datetime.now() >= next_due

    def _finapi_store_connection_meta(self, bank_connection):
        """Persist consent expiry + banking interface from a bank connection.

        Args:
            bank_connection: A finAPI bank connection payload (dict).
        """
        self.ensure_one()
        vals = {}
        expires = self._finapi_extract_consent_expiry(bank_connection)
        if expires:
            vals["finapi_consent_expires_at"] = self._finapi_parse_dt(expires)
        banking_interface = self._finapi_extract_consent_interface(bank_connection)
        if banking_interface:
            vals["finapi_banking_interface"] = banking_interface
        if vals:
            self.sudo().write(vals)

    # ---------- Transaction mapping --------------------------------
    @api.model
    def _finapi_transaction_to_line(self, tx):
        """Map one finAPI transaction dict to an Odoo statement-line dict."""
        tx_id = tx.get("id")
        account_id = tx.get("accountId")
        booking_date = (
            tx.get("bankBookingDate")
            or tx.get("finapiBookingDate")
            or tx.get("valueDate")
        )
        payment_ref = (tx.get("purpose") or "").strip() or _("(no purpose)")
        # unique_import_id prevents duplicates across cron runs
        unique_import_id = f"finapi-{account_id}-{tx_id}"

        vals = {
            "date": booking_date,
            "payment_ref": payment_ref[:255],
            "unique_import_id": unique_import_id,
            "amount": tx.get("amount") or 0.0,
            "ref": (
                tx.get("endToEndReference")
                or tx.get("counterpartMandateReference")
                or ""
            )[:255]
            or False,
            "partner_name": (tx.get("counterpartName") or "")[:255] or False,
            "account_number": (
                tx.get("counterpartIban") or tx.get("counterpartAccountNumber") or ""
            )
            or False,
            "narration": self._finapi_format_narration(tx),
        }
        return vals

    @staticmethod
    def _finapi_format_narration(tx):
        bits = []
        for key in (
            "typeCodeZka",
            "bankTransactionCode",
            "sepaPurposeCode",
            "counterpartBic",
            "counterpartCreditorId",
        ):
            val = tx.get(key)
            if val:
                bits.append(f"{key}: {val}")
        return "\n".join(bits) or False

    # ===============================================================
    # UI actions (buttons on the provider form)
    # ===============================================================
    def action_finapi_create_user(self):
        """Create a finAPI user for this provider. Stores generated
        id/password on the record."""
        self.ensure_one()
        if self.finapi_user_id:
            raise UserError(
                _("This provider already has a finAPI user (%s).")
                % self.finapi_user_id,
            )
        # finAPI limits userId and password to 36 characters. Keep the random
        # suffix intact (collision safety) and truncate the dbname part.
        suffix = f"-{self.id}-{secrets.token_hex(4)}"
        db_part = self.env.cr.dbname[: 36 - len("odoo-") - len(suffix)]
        user_id = f"odoo-{db_part}{suffix}"
        password = secrets.token_urlsafe(24)
        with self._finapi_get_interface() as interface:
            client_token = interface.get_client_token()
            interface.create_user(client_token, user_id=user_id, password=password)
        self.sudo().write(
            {
                "finapi_user_id": user_id,
                "finapi_user_password": password,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("finAPI user created"),
                "message": _("User ID: %s") % user_id,
                "sticky": False,
                "type": "success",
            },
        }

    def action_finapi_open_webform_wizard(self):
        self.ensure_one()
        if not self.finapi_user_id:
            raise UserError(_("Create a finAPI user first."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Add finAPI Bank Connection"),
            "res_model": "finapi.webform.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_provider_id": self.id},
        }

    def action_finapi_refresh_consent(self):
        """Open a bankConnectionUpdate Web Form.

        This is the only allowed way to force an on-demand data refresh /
        renew the PSD2 consent for an UNLICENSED mandator (routine refresh is
        done server-side by finAPI's Automatic Batch Update).
        """
        self.ensure_one()
        if not self.finapi_bank_connection_id:
            raise UserError(_("No bank connection linked yet."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Renew finAPI Consent"),
            "res_model": "finapi.webform.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                "default_provider_id": self.id,
                "default_mode": "update",
            },
        }

    def _finapi_consent_renewal_warning(self, exc):
        """Turn a 'Web Form required' into a warning that offers the wizard.

        finAPI asking for a Web Form is a task for the user, not a crash, so
        the user gets a plain warning with a button that opens the consent
        renewal wizard instead of a stack trace.

        Args:
            exc: The :class:`FinapiWebFormRequiredError` that was raised.

        Returns:
            A :class:`odoo.exceptions.RedirectWarning` ready to be raised.
        """
        self.ensure_one()
        message = _(
            "Your bank requires a new confirmation (SCA) before finAPI can "
            "fetch fresh transactions for %(journal)s. Renew the consent, "
            "then run the refresh again."
        ) % {"journal": self.journal_id.display_name or self.name}
        if exc.webform_url:
            message += "\n\n" + (
                _("finAPI Web Form: %(url)s") % {"url": exc.webform_url}
            )
        action = self.env.ref(
            "account_statement_import_online_finapi."
            "finapi_webform_wizard_update_action"
        )
        return RedirectWarning(
            message,
            action.id,
            _("Renew consent"),
            {
                "default_provider_id": self.id,
                "default_mode": "update",
            },
        )

    def action_finapi_check_connection(self):
        """Refresh consent expiry + banking interface from finAPI and toast."""
        self.ensure_one()
        if not self.finapi_bank_connection_id:
            raise UserError(_("No bank connection linked yet."))
        with self._finapi_get_interface() as interface:
            token = self._finapi_get_user_token(interface)
            bc = interface.get_bank_connection(token, self.finapi_bank_connection_id)
        self._finapi_store_connection_meta(bc)
        expires = self._finapi_extract_consent_expiry(bc)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("finAPI connection OK"),
                "message": _("Consent expires: %s") % (expires or _("unknown")),
                "sticky": False,
                "type": "success",
            },
        }

    def action_finapi_refresh_data_now(self):
        """Force an immediate finAPI data refresh, then import the result.

        Bypasses the throttle so a user can pull the very latest bookings on
        demand (using the configured ``finapi_refresh_mode``). Routine refresh
        otherwise happens automatically inside the scheduled pull.
        """
        self.ensure_one()
        if self.finapi_refresh_mode == "none":
            raise UserError(
                _(
                    "Data refresh is disabled for this provider "
                    "(finAPI Data Refresh = 'No refresh'). Choose the Web Form "
                    "background update or direct update mode first."
                )
            )
        if not self.finapi_bank_connection_id:
            raise UserError(_("No bank connection linked yet."))
        with self._finapi_get_interface() as interface:
            token = self._finapi_get_user_token(interface)
            try:
                self._finapi_refresh_bank_data(interface, token, force=True)
            except FinapiWebFormRequiredError as exc:
                raise self._finapi_consent_renewal_warning(exc) from exc
        # Import what we just refreshed (manual run: errors must surface).
        date_until = fields.Datetime.now()
        date_since = self.last_successful_run or (
            date_until - self._get_next_run_period()
        )
        self._pull(date_since, date_until)
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("finAPI data refreshed"),
                "message": _("Latest transactions fetched and imported."),
                "sticky": False,
                "type": "success",
            },
        }

    # ===============================================================
    # Scheduled actions
    # ===============================================================
    @api.model
    def _finapi_cron_check_consent_expiry(self, days_before=14):
        """Send email alerts for consents expiring within *days_before* days.

        Called by ``ir.cron`` daily.
        """
        threshold = fields.Datetime.add(
            fields.Datetime.now(),
            days=days_before,
        )
        providers = self.search(
            [
                ("service", "=", "finapi"),
                ("finapi_consent_expires_at", "!=", False),
                ("finapi_consent_expires_at", "<=", threshold),
                ("finapi_bank_connection_id", "!=", False),
            ]
        )
        template = self.env.ref(
            "account_statement_import_online_finapi.mail_template_consent_expiry",
            raise_if_not_found=False,
        )
        if not template:
            _logger.warning(
                "finAPI consent-expiry mail template not found — "
                "skipping email alerts."
            )
            return
        for provider in providers:
            if provider.finapi_consent_alert_expiry == (
                provider.finapi_consent_expires_at
            ):
                # Already alerted for this exact expiry — do not spam daily.
                continue
            _logger.info(
                "finAPI consent expiry alert for provider %s (expires %s)",
                provider.name,
                provider.finapi_consent_expires_at,
            )
            template.send_mail(provider.id, force_send=False)
            provider.finapi_consent_alert_expiry = provider.finapi_consent_expires_at

    @staticmethod
    def _finapi_extract_consent_expiry(bank_connection):
        """Return the PSD2 consent expiry timestamp from a bank connection.

        finAPI exposes the consent per banking interface as
        ``interfaces[].aisConsent.expiresAt``. Some payloads also carry a
        top-level ``consent`` object, so both shapes are supported. Returns
        the raw finAPI timestamp string, or ``None`` when no consent is found.

        Args:
            bank_connection: A finAPI bank connection payload (dict).
        """
        bc = bank_connection or {}
        consent = bc.get("consent") or {}
        if consent.get("expiresAt"):
            return consent["expiresAt"]
        for interface in bc.get("interfaces") or []:
            ais_consent = (interface or {}).get("aisConsent") or {}
            if ais_consent.get("expiresAt"):
                return ais_consent["expiresAt"]
        return None

    @staticmethod
    def _finapi_extract_consent_interface(bank_connection):
        """Return the bankingInterface that carries the AIS consent.

        finAPI exposes interfaces under ``interfaces[]``, each optionally with
        an ``aisConsent``. Returns the ``bankingInterface`` of the first
        interface that has a consent, else the first interface's value, else
        ``None``.

        Args:
            bank_connection: A finAPI bank connection payload (dict).
        """
        interfaces = (bank_connection or {}).get("interfaces") or []
        for interface in interfaces:
            interface = interface or {}
            if interface.get("aisConsent") and interface.get("bankingInterface"):
                return interface["bankingInterface"]
        for interface in interfaces:
            if (interface or {}).get("bankingInterface"):
                return interface["bankingInterface"]
        return None

    @staticmethod
    def _finapi_parse_dt(value):
        """Parse finAPI ISO-8601 timestamps like '2026-07-14T08:00:00.000+0000'."""
        if not value:
            return False
        # strip milliseconds and normalise timezone so fromisoformat works
        value = value.replace("Z", "+00:00")
        if "." in value:
            head, _, tail = value.partition(".")
            # tail looks like "000+0000" → keep only timezone
            tz = ""
            for sign in ("+", "-"):
                if sign in tail:
                    tz = sign + tail.split(sign, 1)[1]
                    break
            value = head + tz
        # turn +0000 into +00:00 (only when it really is a numeric offset)
        if len(value) >= 5 and value[-5] in "+-" and value[-4:].isdigit():
            value = value[:-2] + ":" + value[-2:]
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            _logger.warning("finAPI: could not parse datetime %s", value)
            return False
        if parsed.tzinfo is not None:
            # Odoo stores naive UTC — convert instead of dropping the offset
            parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
