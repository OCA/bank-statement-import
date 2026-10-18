# Copyright 2026 Agent ERP GmbH (https://www.agenterp.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl-3.0)
import json
import logging

import requests

from odoo.exceptions import UserError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

DEFAULT_TIMEOUT = 60  # seconds
# A bank connection update makes finAPI talk to the bank live, which can take
# noticeably longer than a plain read -- give it a much larger budget.
UPDATE_TIMEOUT = 180  # seconds
USER_AGENT = "odoo-account_statement_import_online_finapi/16.0.1.0.0"


class FinapiAuthError(UserError):
    """Raised when finAPI rejects our credentials / tokens."""


class FinapiApiError(UserError):
    """Raised for any non-auth error returned by finAPI."""


class FinapiWebFormRequiredError(FinapiApiError):
    """Raised when finAPI can only continue with an interactive Web Form.

    That is the regular PSD2 outcome once a consent expires or the bank asks
    for SCA -- nothing is broken, the user simply has to confirm in the bank's
    web form. The URL finAPI generated is kept as an attribute so callers can
    send the user straight there instead of burying it in a message.
    """

    def __init__(self, message, webform_url=None):
        super().__init__(message)
        self.webform_url = webform_url


class FinapiInterface:
    """Stateless HTTP client.

    The caller is responsible for persisting tokens between invocations.
    Instance-level ``_user_token`` is only kept for the duration of a single
    pull so that the automatic 401-retry works without re-passing credentials
    all the way down.
    """

    def __init__(
        self,
        base_url,
        client_id,
        client_secret,
        timeout=DEFAULT_TIMEOUT,
        webform_base_url=None,
    ):
        self.base_url = (base_url or "").rstrip("/")
        self.webform_base_url = (webform_base_url or "").rstrip("/") or self.base_url
        self.client_id = client_id
        self.client_secret = client_secret
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
            }
        )

    # ---------------------------------------------------------------
    # Session lifecycle
    # ---------------------------------------------------------------
    def close(self):
        """Release the underlying TCP connection pool."""
        self._session.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        # Safety net for callers that do not use close()/context manager —
        # avoids leaking file descriptors in long-running Odoo workers.
        try:
            self._session.close()
        except Exception:  # noqa: BLE001 — interpreter may be shutting down
            _logger.debug("finAPI: closing the HTTP session failed", exc_info=True)

    # ---------------------------------------------------------------
    # Low-level request helper
    # ---------------------------------------------------------------
    def _request(
        self,
        method,
        path,
        token=None,
        params=None,
        json_body=None,
        data=None,
        expected_status=(200, 201),
        base_url=None,
        timeout=None,
    ):
        url = f"{base_url or self.base_url}{path}"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if json_body is not None:
            headers["Content-Type"] = "application/json"
        try:
            response = self._session.request(
                method,
                url,
                params=params,
                json=json_body,
                data=data,
                headers=headers,
                timeout=timeout or self.timeout,
            )
        except requests.RequestException as exc:
            raise FinapiApiError(
                _("finAPI connection error (%(method)s %(path)s): %(error)s")
                % {"method": method, "path": path, "error": exc}
            ) from exc

        if response.status_code in expected_status:
            if not response.content:
                return {}
            try:
                return response.json()
            except ValueError as exc:
                raise FinapiApiError(
                    _("finAPI returned non-JSON payload on %(path)s") % {"path": path}
                ) from exc

        # Error handling ------------------------------------------------
        request_id = response.headers.get("X-Request-Id", "-")
        body_preview = response.text[:500]
        _logger.warning(
            "finAPI error %s on %s %s — requestId=%s — body=%s",
            response.status_code,
            method,
            path,
            request_id,
            body_preview,
        )

        if response.status_code == 401:
            raise FinapiAuthError(
                _(
                    "finAPI rejected our access token "
                    "(HTTP 401, requestId=%(rid)s).\n%(body)s"
                )
                % {"rid": request_id, "body": body_preview}
            )

        message = body_preview
        try:
            payload = response.json()
            errors = payload.get("errors") or []
            if errors:
                message = errors[0].get("message") or message
        except ValueError:
            _logger.debug("finAPI error body is not valid JSON")
        raise FinapiApiError(
            _(
                "finAPI error %(status)s on %(method)s %(path)s "
                "(requestId=%(rid)s): %(msg)s"
            )
            % {
                "status": response.status_code,
                "method": method,
                "path": path,
                "rid": request_id,
                "msg": message,
            }
        )

    # ---------------------------------------------------------------
    # OAuth
    # ---------------------------------------------------------------
    def get_client_token(self):
        """Client-credentials grant — used for user management only."""
        payload = self._request(
            "POST",
            "/api/v2/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
        )
        if not payload.get("access_token"):
            raise FinapiAuthError(_("finAPI did not return a client access_token."))
        return payload["access_token"]

    def get_user_token(self, username, password):
        """Password grant — used for all user-scoped calls."""
        payload = self._request(
            "POST",
            "/api/v2/oauth/token",
            data={
                "grant_type": "password",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "username": username,
                "password": password,
            },
        )
        if not payload.get("access_token"):
            raise FinapiAuthError(_("finAPI did not return a user access_token."))
        return payload  # caller persists access_token + refresh_token

    def refresh_user_token(self, refresh_token):
        payload = self._request(
            "POST",
            "/api/v2/oauth/token",
            data={
                "grant_type": "refresh_token",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "refresh_token": refresh_token,
            },
        )
        if not payload.get("access_token"):
            raise FinapiAuthError(
                _("finAPI did not return a refreshed user access_token.")
            )
        return payload

    # ---------------------------------------------------------------
    # User management
    # ---------------------------------------------------------------
    def create_user(self, client_token, user_id=None, password=None, email=None):
        body = {}
        if user_id:
            body["id"] = user_id
        if password:
            body["password"] = password
        if email:
            body["email"] = email
        return self._request(
            "POST",
            "/api/v2/users",
            token=client_token,
            json_body=body,
        )

    # ---------------------------------------------------------------
    # Web Form 2.0
    # ---------------------------------------------------------------
    def create_webform_import(self, user_token, redirect_url=None, callback_url=None):
        """Create an `importBankConnection` web form. Returns the raw payload
        (contains ``id``, ``url``).

        Web Form 2.0 is a separate API hosted on ``webform_base_url``.
        The Access API user token is accepted by the Web Form host.
        """
        body = {}
        if redirect_url:
            body["redirectUrl"] = redirect_url
        if callback_url:
            body["callbacks"] = {"finalised": callback_url}
        return self._request(
            "POST",
            "/api/webForms/bankConnectionImport",
            token=user_token,
            json_body=body,
            expected_status=(200, 201),
            base_url=self.webform_base_url,
        )

    def create_webform_update(
        self, user_token, bank_connection_id, redirect_url=None, callback_url=None
    ):
        """Create a ``bankConnectionUpdate`` web form for consent renewal.

        NOTE: this legacy Web Form endpoint is superseded by the background
        update task (:meth:`start_background_update`), which is the supported
        way to refresh/renew a bank connection in Web Form 2.0. Kept for the
        interactive consent-renewal wizard; see ROADMAP.
        """
        body = {
            "bankConnectionId": int(bank_connection_id),
        }
        if redirect_url:
            body["redirectUrl"] = redirect_url
        if callback_url:
            body["callbacks"] = {"finalised": callback_url}
        return self._request(
            "PUT",
            "/api/webForms/bankConnectionUpdate",
            token=user_token,
            json_body=body,
            expected_status=(200, 201),
            base_url=self.webform_base_url,
        )

    def get_webform(self, user_token, webform_id):
        return self._request(
            "GET",
            f"/api/webForms/{webform_id}",
            token=user_token,
            base_url=self.webform_base_url,
        )

    # ---------------------------------------------------------------
    # Web Form 2.0 — background update task (refresh an existing
    # bank connection). This is the Web Form 2.0 way to refresh data;
    # the Access API ``POST /bankConnections/update`` is only allowed
    # for licensed mandators. Within a valid recurring consent the task
    # completes WITHOUT user interaction (``COMPLETED``); otherwise it
    # reports ``WEB_FORM_REQUIRED`` with a web form URL for SCA.
    # ---------------------------------------------------------------
    def start_background_update(
        self, user_token, bank_connection_id, redirect_url=None, callback_url=None
    ):
        """Start a ``backgroundUpdate`` task to refresh a bank connection.

        Returns the created ``Task`` payload (``id``, ``status``, ...). Poll
        :meth:`get_task` until the status is terminal.

        Args:
            user_token: A valid finAPI user access token.
            bank_connection_id: finAPI bank connection to refresh.
            redirect_url: Optional URL the user returns to after an
                interactive (SCA) completion.
            callback_url: Optional webhook URL for finalised /
                web-form-required notifications.
        """
        body = {"bankConnectionId": int(bank_connection_id)}
        if redirect_url:
            body["redirectUrl"] = redirect_url
        if callback_url:
            body["callbacks"] = {
                "finalised": callback_url,
                "webFormRequired": callback_url,
            }
        return self._request(
            "POST",
            "/api/tasks/backgroundUpdate",
            token=user_token,
            json_body=body,
            expected_status=(200, 201),
            base_url=self.webform_base_url,
            timeout=UPDATE_TIMEOUT,
        )

    def get_task(self, user_token, task_id):
        """Return a Web Form 2.0 task (status + payload) by id."""
        return self._request(
            "GET",
            f"/api/tasks/{task_id}",
            token=user_token,
            base_url=self.webform_base_url,
        )

    # ---------------------------------------------------------------
    # Bank connections & accounts
    # ---------------------------------------------------------------
    def list_bank_connections(self, user_token):
        """Return all bank connections for the authenticated user."""
        payload = self._request(
            "GET",
            "/api/v2/bankConnections",
            token=user_token,
        )
        return payload.get("connections", [])

    def get_bank_connection(self, user_token, bank_connection_id):
        return self._request(
            "GET",
            f"/api/v2/bankConnections/{bank_connection_id}",
            token=user_token,
        )

    def update_bank_connection(
        self,
        user_token,
        bank_connection_id,
        banking_interface=None,
        timeout=UPDATE_TIMEOUT,
    ):
        """Trigger a customer-not-present data update for a bank connection.

        ``GET /transactions`` only ever returns the data finAPI already has
        stored. Without an explicit update finAPI never fetches new bookings
        from the bank, so recurring statement pulls keep returning the same
        (stale) set. This call asks finAPI to fetch fresh data from the bank.

        This is only permitted for **licensed** mandators (clients holding
        their own PSD2/TPP license). For UNLICENSED mandators finAPI rejects
        the call (HTTP 4xx, "direct API calls not allowed, use the Web Form")
        and the Web Form update flow must be used instead. Within a valid
        recurring AIS consent, PSD2 allows a limited number (typically four)
        of such customer-not-present accesses per day.

        Args:
            user_token: A valid finAPI user access token.
            bank_connection_id: finAPI bank connection to refresh.
            banking_interface: Banking interface to update through, e.g.
                ``"XS2A"``. finAPI needs it to pick the consent-bearing
                interface; omitting it can yield an HTTP 400. ``None`` lets
                finAPI choose.
            timeout: Per-call timeout in seconds (defaults to
                ``UPDATE_TIMEOUT`` because bank round-trips are slow).

        Returns:
            dict: The updated bank connection payload.

        Raises:
            FinapiAuthError: finAPI rejected the access token.
            FinapiApiError: Update failed (e.g. SCA / consent required, or
                the mandator is not licensed for direct updates).
        """
        body = {"bankConnectionId": int(bank_connection_id)}
        if banking_interface:
            body["bankingInterface"] = banking_interface
        return self._request(
            "POST",
            "/api/v2/bankConnections/update",
            token=user_token,
            json_body=body,
            timeout=timeout,
        )

    def list_accounts(self, user_token, bank_connection_id):
        payload = self._request(
            "GET",
            "/api/v2/accounts",
            token=user_token,
            params={"bankConnectionIds": bank_connection_id, "perPage": 500},
        )
        return payload.get("accounts", [])

    def get_account(self, user_token, account_id):
        return self._request(
            "GET",
            f"/api/v2/accounts/{account_id}",
            token=user_token,
        )

    # ---------------------------------------------------------------
    # Transactions (paginated)
    # ---------------------------------------------------------------
    def list_transactions(
        self, user_token, account_id, date_from, date_to, per_page=500
    ):
        """Return **all** transactions for an account within the date range.

        ``date_from`` / ``date_to`` must be ``datetime.date`` (or string
        ``YYYY-MM-DD``). Iterates over pages until ``paging.pageCount`` is
        reached.
        """
        if hasattr(date_from, "isoformat"):
            date_from = date_from.isoformat()
        if hasattr(date_to, "isoformat"):
            date_to = date_to.isoformat()
        out = []
        page = 1
        while True:
            payload = self._request(
                "GET",
                "/api/v2/transactions",
                token=user_token,
                params={
                    "view": "bankView",
                    "accountIds": account_id,
                    "minBankBookingDate": date_from,
                    "maxBankBookingDate": date_to,
                    "page": page,
                    "perPage": per_page,
                    "order": "bankBookingDate,asc",
                },
            )
            out.extend(payload.get("transactions", []))
            paging = payload.get("paging") or {}
            page_count = paging.get("pageCount") or 1
            if page >= page_count:
                break
            page += 1
        return out

    # ---------------------------------------------------------------
    # Utility
    # ---------------------------------------------------------------
    @staticmethod
    def pretty(payload):
        try:
            return json.dumps(payload, indent=2, ensure_ascii=False)
        except (TypeError, ValueError):
            return str(payload)
