# Copyright 2022 ForgeFlow S.L.
# Copyright 2023-2024 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
from datetime import datetime
from uuid import uuid4

import requests
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

GOCARDLESS_API = "https://bankaccountdata.gocardless.com/api/v2/"
REQUESTS_TIMEOUT = 60


class OnlineBankStatementProvider(models.Model):
    _inherit = "online.bank.statement.provider"

    gocardless_token = fields.Char(readonly=True)
    gocardless_token_expiration = fields.Datetime(readonly=True)
    gocardless_refresh_token = fields.Char(readonly=True)
    gocardless_refresh_expiration = fields.Datetime(readonly=True)
    gocardless_requisition_ref = fields.Char(readonly=True)
    gocardless_requisition_id = fields.Char(readonly=True)
    gocardless_requisition_expiration = fields.Datetime(readonly=True)
    gocardless_institution_id = fields.Char()
    gocardless_account_id = fields.Char()
    gocardless_country_id = fields.Many2one(
        "res.country",
        compute="_compute_gocardless_country_id",
        store=True,
        readonly=False,
    )

    @api.depends("journal_id", "company_id")
    def _compute_gocardless_country_id(self):
        for provider in self:
            provider.gocardless_country_id = (
                provider.journal_id.bank_account_id.company_id
                or provider.journal_id.company_id
            ).country_id

    def gocardless_reset_requisition(self):
        self.write(
            {
                "gocardless_requisition_id": False,
                "gocardless_requisition_ref": False,
                "gocardless_requisition_expiration": False,
            }
        )

    @api.model
    def _get_available_services(self):
        """Include the new service GoCardless in the online providers."""
        return super()._get_available_services() + [
            ("gocardless", "GoCardless"),
        ]

    def _gocardless_get_headers(self, basic=False):
        """Generic method for providing the needed request headers."""
        self.ensure_one()
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        if not basic:
            headers["Authorization"] = f"Bearer {self._gocardless_get_token()}"
        return headers

    def _gocardless_request(
        self, endpoint, request_type="get", params=None, data=None, basic_auth=False
    ):
        content = {}
        url = url_join(GOCARDLESS_API, endpoint) + "/"
        response = getattr(requests, request_type)(
            url,
            data=data,
            params=params,
            headers=self._gocardless_get_headers(basic=basic_auth),
            timeout=REQUESTS_TIMEOUT,
        )
        if response.status_code == 429:  # Rate limit overpassed
            raise UserError(json.loads(response.text)["detail"])
        if response.status_code in [200, 201]:
            content = json.loads(response.text)
        return response, content

    def _gocardless_get_token(self):
        """Resolve and return the corresponding GoCardless token for doing the requests.
        If there's still no token, it's requested. If it exists, but it's expired and
        the refresh token isn't, a refresh is requested.
        """
        self.ensure_one()
        now = fields.Datetime.now()
        if not self.gocardless_token or now > self.gocardless_token_expiration:
            # Refresh token
            if (
                self.gocardless_refresh_token
                and now < self.gocardless_refresh_expiration
            ):
                endpoint = "token/refresh"
                request_data = {"refresh": self.gocardless_refresh_token}
            else:
                endpoint = "token/new"
                request_data = {"secret_id": self.username, "secret_key": self.password}
            _response, data = self._gocardless_request(
                endpoint,
                request_type="post",
                data=json.dumps(request_data),
                basic_auth=True,
            )
            expiration_date = now + relativedelta(seconds=data.get("access_expires", 0))
            vals = {
                "gocardless_token": data.get("access", False),
                "gocardless_token_expiration": expiration_date,
            }
            if data.get("refresh"):
                vals["gocardless_refresh_token"] = data["refresh"]
                vals["gocardless_refresh_expiration"] = now + relativedelta(
                    seconds=data["refresh_expires"]
                )
            self.sudo().write(vals)
        return self.gocardless_token

    def action_select_gocardless_bank(self):
        if not self.journal_id.bank_account_id:
            raise UserError(
                _("To continue configure bank account on journal %s")
                % (self.journal_id.display_name)
            )
        # Check if there's another existing provider for the same bank institution,
        # and ask for reusing it for this bank account, as some banks don't allow
        # several requisitions from the same source (GoCardless).
        other = self.search(
            [
                ("service", "=", "gocardless"),
                ("gocardless_requisition_id", "!=", False),
                ("journal_id.bank_id", "=", self.journal_id.bank_id.id),
                ("id", "!=", self.id),
            ],
            limit=1,
        )
        if other:
            wizard = self.env["online.bank.statement.provider.existing"].create(
                {
                    "provider_id": self.id,
                    "other_provider_id": other.id,
                }
            )
            return {
                "type": "ir.actions.act_window",
                "res_model": wizard._name,
                "res_id": wizard.id,
                "name": _("Existing link"),
                "view_mode": "form",
                "target": "new",
            }
        return self._gocardless_select_bank_institution()

    def _gocardless_select_bank_institution(self):
        """Ask for the GoCardless bank instituion and continue full linkage."""
        country = self.gocardless_country_id
        response, data = self._gocardless_request(
            "institutions", params={"country": country.code}
        )
        if response.status_code == 400:
            raise UserError(_("Incorrect country code or country not supported."))
        institutions = data
        # Prepare data for being showed in the JS widget
        ctx = self.env.context.copy()
        ctx.update(
            {
                "dialog_size": "medium",
                "country": country.code,
                "country_name": country.name,
                "provider_id": self.id,
                "institutions": institutions,
                "country_names": [{"code": country.code, "name": country.name}],
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "online_sync_institution_selector_gocardless",
            "name": _("Select Bank of your Account"),
            "params": {},
            "target": "new",
            "context": ctx,
        }

    def action_check_gocardless_agreement(self):
        self.ensure_one()
        self.gocardless_requisition_ref = str(uuid4())
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        redirect_url = url_join(base_url, "gocardless/response")
        _response, data = self._gocardless_request(
            "requisitions",
            request_type="post",
            data=json.dumps(
                {
                    "redirect": redirect_url,
                    "institution_id": self.gocardless_institution_id,
                    "reference": self.gocardless_requisition_ref,
                }
            ),
        )
        if data:
            requisition_data = data
            self.gocardless_requisition_id = requisition_data["id"]
            # JS code expects here to return a plain link or nothing
            return requisition_data["link"]

    def _gocardless_request_requisition(self):
        _response, data = self._gocardless_request(
            f"requisitions/{self.gocardless_requisition_id}"
        )
        return data

    def _gocardless_request_account(self, account_id):
        _response, data = self._gocardless_request(f"accounts/{account_id}")
        return data

    def _gocardless_request_agreement(self, agreement_id):
        _response, data = self._gocardless_request(f"agreements/enduser/{agreement_id}")
        return data

    def _gocardless_finish_requisition(self, dry=False):
        """Once the requisiton to the bank institution has been made, and this is called
        from the controller assigned to the redirect URL, we check that the IBAN account
        of the linked journal is included in the accessible bank accounts, and if so,
        we set the rest of the needed data.

        A message in the chatter is logged both for sucessful or failed operation (this
        last one only if not in dry mode).

        :param: dry: If true, this is called as previous step before starting the whole
          process, so no fail message is logged in chatter in this case.
        """
        self.ensure_one()
        requisition_data = self._gocardless_request_requisition()
        accounts = requisition_data.get("accounts", [])
        found_account = False
        accounts_iban = []
        for account_id in accounts:
            account_data = self._gocardless_request_account(account_id)
            if account_data:
                accounts_iban.append(account_data["iban"])
                if (
                    self.journal_id.bank_account_id.sanitized_acc_number
                    == account_data["iban"].upper()
                ):
                    found_account = True
                    self.gocardless_account_id = account_data["id"]
                    break
        if found_account:
            agreement_data = self._gocardless_request_agreement(
                requisition_data["agreement"]
            )
            self.gocardless_requisition_expiration = datetime.strptime(
                agreement_data["accepted"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ) + relativedelta(days=agreement_data["access_valid_for_days"])
            self.sudo().message_post(
                body=_("Your account number %(iban_number)s is successfully attached.")
                % {"iban_number": self.journal_id.bank_account_id.display_name}
            )
            return True
        elif not dry:
            self.sudo().write(
                {
                    "gocardless_requisition_expiration": False,
                    "gocardless_requisition_id": False,
                    "gocardless_requisition_ref": False,
                }
            )
            self.sudo().message_post(
                body=_(
                    "Your account number %(iban_number)s it's not in the IBAN "
                    "account numbers found %(accounts_iban)s, please check"
                )
                % {
                    "iban_number": self.journal_id.bank_account_id.display_name,
                    "accounts_iban": " / ".join(accounts_iban),
                }
            )
        return False

    def _obtain_statement_data(self, date_since, date_until):
        """Generic online cron overrided for acting when the sync is for GoCardless."""
        self.ensure_one()
        if self.service == "gocardless":
            return self._gocardless_obtain_statement_data(date_since, date_until)
        return super()._obtain_statement_data(date_since, date_until)

    def _gocardless_request_transactions(self, date_since, date_until):
        """Method for requesting GoCardless transactions.
        Isolated for being mocked in tests.
        """
        # We can't query dates in the future in GoCardless
        now = fields.Datetime.now()
        if now > date_since and now < date_until:
            date_until = now
        _response, data = self._gocardless_request(
            f"accounts/{self.gocardless_account_id}/transactions",
            params={
                "date_from": date_since.strftime(DF),
                "date_to": date_until.strftime(DF),
            },
        )
        return data

    def _gocardless_obtain_statement_data(self, date_since, date_until):
        """Called from the cron or the manual pull wizard to obtain transactions for
        the given period.
        """
        self.ensure_one()
        if not self.gocardless_account_id:
            return
        currency_model = self.env["res.currency"]
        if self.gocardless_requisition_expiration <= fields.Datetime.now():
            self.sudo().message_post(
                body=_(
                    "You should renew the authorization process with your bank "
                    "institution for GoCardless."
                )
            )
            return [], {}
        own_acc_number = self.journal_id.bank_account_id.sanitized_acc_number
        transactions = self._gocardless_request_transactions(date_since, date_until)
        res = []
        sequence = 0
        currencies_cache = {}
        for tr in transactions.get("transactions", {}).get("booked", []):
            # Reference: https://developer.gocardless.com/bank-account-data/transactions
            string_date = tr.get("valueDate") or tr.get("bookingDate")
            # CHECK ME: if there's not date string, is transaction still valid?
            if not string_date:
                continue
            current_date = fields.Date.from_string(string_date)
            sequence += 1
            amount = float(tr.get("transactionAmount", {}).get("amount", 0.0))
            currency_code = tr.get("transactionAmount", {}).get(
                "currency", self.journal_id.currency_id.name
            )
            currency = currencies_cache.get(currency_code)
            if not currency:
                currency = currency_model.search([("name", "=", currency_code)])
                currencies_cache[currency_code] = currency
            amount_currency = amount
            if (
                currency
                and self.journal_id.currency_id
                and currency != self.journal_id.currency_id
            ):
                amount_currency = currency._convert(
                    amount,
                    self.journal_id.currency_id,
                    self.journal_id.company_id,
                    current_date,
                )
            if amount_currency >= 0:
                partner_name = tr.get("debtorName", False)
            else:
                partner_name = tr.get("creditorName", False)
            account_number = tr.get("debtorAccount", {}).get("iban") or tr.get(
                "creditorAccount", {}
            ).get("iban", False)
            if account_number == own_acc_number:
                account_number = False  # Discard own bank account number
            if "remittanceInformationUnstructured" in tr:
                payment_ref = tr["remittanceInformationUnstructured"]
            elif "remittanceInformationUnstructuredArray" in tr:
                payment_ref = " ".join(tr["remittanceInformationUnstructuredArray"])
            else:
                payment_ref = partner_name
            res.append(
                {
                    "sequence": sequence,
                    "date": current_date,
                    "ref": partner_name or "/",
                    "payment_ref": payment_ref,
                    "unique_import_id": self._gocardless_get_unique_import_id(tr),
                    "amount": amount_currency,
                    "account_number": account_number,
                    "partner_name": partner_name,
                    "transaction_type": tr.get("bankTransactionCode", ""),
                    "narration": self._gocardless_get_note(tr),
                }
            )
        return res, {}

    def _gocardless_get_unique_import_id(self, tr):
        return (
            tr.get("entryReference")
            or tr.get("transactionId")
            or tr.get("internalTransactionId")
        )

    def _gocardless_get_note(self, tr):
        """Override to get different notes."""
        note_elements = [
            "additionalInformation",
            "balanceAfterTransaction",
            "bankTransactionCode",
            "bookingDate",
            "checkId",
            "creditorAccount",
            "creditorAgent",
            "creditorId",
            "creditorName",
            "currencyExchange",
            "debtorAccount",
            "debtorAgent",
            "debtorName",
            "entryReference",
            "mandateId",
            "proprietaryBank",
            "remittanceInformation Unstructured",
            "transactionAmount",
            "transactionId",
            "ultimateCreditor",
            "ultimateDebtor",
            "valueDate",
        ]
        notes = [str(tr[element]) for element in note_elements if tr.get(element)]
        return "\n".join(notes)
