# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import logging
import re
from datetime import datetime
from uuid import uuid4

import requests
from dateutil.relativedelta import relativedelta
from werkzeug.urls import url_encode, url_join

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

_logger = logging.getLogger(__name__)

NORDIGEN_ENDPOINT = "https://ob.nordigen.com/api/v2"
SANDBOX_INSTITUTION_ID = "SANDBOXFINANCE_SFIN0000"


class OnlineBankStatementProviderNordigen(models.Model):
    _inherit = "online.bank.statement.provider"

    nordigen_token = fields.Char(readonly=True)
    nordigen_token_expiration = fields.Datetime(readonly=True, tracking=True)
    nordigen_last_requisition_ref = fields.Char(readonly=True)
    nordigen_last_requisition_id = fields.Char(readonly=True)
    nordigen_last_requisition_expiration = fields.Datetime(readonly=True, tracking=True)
    nordigen_institution_id = fields.Char(related="journal_id.nordigen_institution_id")
    nordigen_account_id = fields.Char(
        related="journal_id.bank_account_id.nordigen_account_id"
    )

    def nordigen_reset_last_identifier(self):
        self.write(
            {
                "nordigen_last_requisition_id": False,
                "nordigen_last_requisition_ref": False,
                "nordigen_last_requisition_expiration": False,
            }
        )

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("nordigen", "Nordigen"),
        ]

    def _get_nordigen_headers(self, token=None):
        headers = {
            "accept": "application/json",
            "Content-Type": "application/json",
        }
        if token:
            headers.update({"Authorization": "Bearer %s" % (token)})
        return headers

    def _update_token_nordigen(self):
        if (
            not self.nordigen_token
            or not self.nordigen_token_expiration
            or self.nordigen_token_expiration <= fields.Datetime.now()
        ):
            url = NORDIGEN_ENDPOINT + "/token/new/"
            response = requests.post(
                url,
                data=json.dumps(
                    {
                        "secret_id": self.username,
                        "secret_key": self.password,
                    }
                ),
                headers=self._get_nordigen_headers(),
            )
            token_data = {}
            if response.status_code == 200:
                token_data = json.loads(response.text)
            self.sudo().nordigen_token = token_data.get("access", False)
            expiration_date = fields.Datetime.now() + relativedelta(
                seconds=token_data.get("access_expires", False)
            )
            self.sudo().nordigen_token_expiration = expiration_date

    def _get_nordigen_institutions(self, country_code=""):
        try:
            url = NORDIGEN_ENDPOINT + "/institutions/"
            response = requests.get(
                url,
                params={
                    "country": country_code,
                },
                headers=self._get_nordigen_headers(self.nordigen_token),
            )
            if response.status_code == 200:
                institutions = json.loads(response.text)
                return institutions
            else:
                return []
        except Exception as e:
            _logger.debug("Getting Institutions  %s", e)
            return []

    def _check_bank_account_nordigen(self):
        if not self.journal_id.bank_account_id:
            raise UserError(
                _("To continue configure bank account on journal %s")
                % (self.journal_id.display_name)
            )

    def action_select_nordigen_bank(self):
        country_model = self.env["res.country"]
        self._check_bank_account_nordigen()
        ctx = self.env.context.copy()
        country = self.company_id.country_id
        self._update_token_nordigen()
        institutions = self._get_nordigen_institutions()
        country_codes = []
        for institution in institutions:
            country_codes += institution["countries"]
        country_codes = list(set(country_codes))
        countries = country_model.search([("code", "in", country_codes)])
        country_names = [{"code": c.code, "name": c.name} for c in countries]
        ctx.update(
            {
                "dialog_size": "medium",
                "country": country.code,
                "country_name": country.name,
                "journal_id": self.journal_id.id,
                "institutions": institutions,
                "country_names": country_names,
            }
        )
        return {
            "type": "ir.actions.client",
            "tag": "online_sync_institution_selector_nordigen",
            "name": _("Select Bank of your Account"),
            "params": {},
            "target": "new",
            "context": ctx,
        }

    def _create_redirect_url_nordigen(self):
        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        return url_join(base_url, "nordigen/response")

    def action_check_agreement(self):
        self._update_token_nordigen()
        institution_id = self.nordigen_institution_id
        if (
            self.env["ir.module.module"]
            .sudo()
            .search(
                [("name", "=", "account_bank_statement_import_online_nordigen")],
                limit=1,
            )
            .demo
        ):
            institution_id = SANDBOX_INSTITUTION_ID
        self.nordigen_last_requisition_ref = str(uuid4())
        url = NORDIGEN_ENDPOINT + "/requisitions/"
        response = requests.post(
            url,
            data=json.dumps(
                {
                    "redirect": self._create_redirect_url_nordigen(),
                    "institution_id": institution_id,
                    "reference": self.nordigen_last_requisition_ref,
                }
            ),
            headers=self._get_nordigen_headers(self.nordigen_token),
        )
        if response.status_code == 201:
            requisition_data = json.loads(response.text)
            redirect_url = requisition_data.get("link", False)
            self.nordigen_last_requisition_id = requisition_data.get("id", False)
            return redirect_url
        return self._create_redirect_url_nordigen()

    def _get_nordigen_agreement_validity(self, agreement_id):
        self._update_token_nordigen()
        agreement_data = {}
        url = NORDIGEN_ENDPOINT + "/agreements/enduser/" + agreement_id + "/"
        agreement_response = requests.get(
            url,
            headers=self._get_nordigen_headers(self.nordigen_token),
        )
        if agreement_response.status_code == 200:
            agreement_data = json.loads(agreement_response.text)
        return agreement_data

    def _get_nordigen_requisition_data(self, requisition_id):
        self._update_token_nordigen()
        requisition_data = {}
        url = NORDIGEN_ENDPOINT + "/requisitions/" + requisition_id + "/"
        requisition_response = requests.get(
            url,
            headers=self._get_nordigen_headers(self.nordigen_token),
        )
        if requisition_response.status_code == 200:
            requisition_data = json.loads(requisition_response.text)
        return requisition_data

    def update_nordigen_request(self):
        self._update_token_nordigen()
        accounts = []
        requisition_data = self._get_nordigen_requisition_data(
            self.nordigen_last_requisition_id
        )
        if requisition_data:
            accounts = requisition_data["accounts"]
            agreement_data = self._get_nordigen_agreement_validity(
                requisition_data["agreement"]
            )
            if agreement_data:
                self.nordigen_last_requisition_expiration = datetime.strptime(
                    agreement_data["accepted"], "%Y-%m-%dT%H:%M:%S.%fZ"
                ) + relativedelta(days=agreement_data["access_valid_for_days"])
        found_account = False
        accounts_iban = []
        for account_id in accounts:
            url = NORDIGEN_ENDPOINT + "/accounts/" + account_id + "/"
            account_response = requests.get(
                url,
                headers=self._get_nordigen_headers(self.nordigen_token),
            )
            if account_response.status_code == 200:
                account_data = json.loads(account_response.text)
                accounts_iban.append(account_data["iban"])
                current_bank_account = self.journal_id.bank_account_id.filtered(
                    lambda x: x.sanitized_acc_number == account_data["iban"]
                )
                if current_bank_account:
                    current_bank_account.write(
                        {"nordigen_account_id": account_data["id"]}
                    )
                    found_account = True
                    self.sudo().message_post(
                        body=_("Your account number %s it successfully attached")
                        % (self.journal_id.bank_account_id.display_name,)
                    )
                    break
        if not found_account:
            self.sudo().write(
                {
                    "nordigen_last_requisition_expiration": False,
                    "nordigen_last_requisition_id": False,
                    "nordigen_last_requisition_ref": False,
                }
            )
            self.sudo().message_post(
                body=_(
                    "Your account number %s it not in iban "
                    "accounts numbers founded %s, please check"
                )
                % (
                    self.journal_id.bank_account_id.display_name,
                    " / ".join(accounts_iban),
                )
            )
            return False
        return True

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "nordigen":
            return super()._obtain_statement_data(date_since, date_until)
        return self._nordigen_obtain_statement_data(date_since, date_until)

    def _nordigen_get_ref(self, tr):
        """Override to change behaviour"""
        amount = float(tr.get("transactionAmount", {}).get("amount", 0.0))
        if amount >= 0:
            partner_name = tr.get("debtorName", "") or ""
        else:
            partner_name = tr.get("creditorName", "") or ""
        ref_list = []
        ref_list.append(partner_name)
        ref = " ".join(ref_list)
        return ref

    def _nordigen_get_note_elements(self):
        return [
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

    def _nordigen_get_note(self, tr):
        """Override to change behaviour"""
        notes = []
        for element in self._nordigen_get_note_elements():
            if element in tr.keys() and tr[element]:
                notes.append(element + ": " + str(tr[element]))
        return "\n".join(notes)

    def _nordigen_get_transactions(self, account_id, date_since, date_until):
        self._update_token_nordigen()
        currency_model = self.env["res.currency"]
        synchronization_message = False
        url = self._get_nordigen_url_action()
        if self.nordigen_last_requisition_id:
            if not self.nordigen_last_requisition_expiration:
                synchronization_message = (
                    _(
                        "You should complete authorization process "
                        "for your bank account with Nordigen "
                        "<a href=%s>Click here</a> to complete "
                        "process in configuration page"
                    )
                    % url
                )
            elif self.nordigen_last_requisition_expiration <= fields.Datetime.now():
                synchronization_message = (
                    _(
                        "You should renew authorization process "
                        "for your bank account with Nordigen "
                        "<a href=%s>Click here</a> to complete "
                        "process in configuration page"
                    )
                    % url
                )
        else:
            synchronization_message = (
                _(
                    "You should complete authorization process"
                    " for your bank account with Nordigen "
                    "<a href=%s>Click here</a> to complete "
                    "process in configuration page"
                )
                % url
            )
        if synchronization_message:
            self.env.user.notify_danger(message=synchronization_message)
            return []
        try:
            transactions = []
            url = NORDIGEN_ENDPOINT + "/accounts/" + account_id + "/transactions/"
            transaction_response = requests.get(
                url,
                params={
                    "date_from": date_since.strftime(DF),
                    "date_to": date_until.strftime(DF),
                },
                headers=self._get_nordigen_headers(self.nordigen_token),
            )
            if transaction_response.status_code == 200:
                transactions = json.loads(transaction_response.text)
            res = []
            sequence = 0
            if not transactions:
                return res
            for tr in transactions.get("transactions", {}).get("booked", []):
                string_date = tr.get("bookingDate") or tr.get("valueDate")
                # CHECK ME: if there's not date string, is transaction still valid?
                if not string_date:
                    continue
                current_date = fields.Date.from_string(string_date)
                sequence += 1
                amount = float(tr.get("transactionAmount", {}).get("amount", 0.0))
                currency_code = tr.get("transactionAmount", {}).get(
                    "currency", self.journal_id.currency_id.name
                )
                current_currency = currency_model.search([("name", "=", currency_code)])
                amount_currency = amount
                if (
                    current_currency
                    and self.journal_id.currency_id
                    and current_currency != self.journal_id.currency_id
                ):
                    amount_currency = current_currency._convert(
                        amount,
                        self.journal_id.currency_id,
                        self.journal_id.company_id,
                        current_date,
                    )
                # Reference:
                # https://nordigen.com/en/docs/account-information/output/transactions/
                if amount_currency >= 0:
                    partner_name = tr.get("debtorName", "") or ""
                else:
                    partner_name = tr.get("creditorName", "") or ""
                ref = self._nordigen_get_ref(tr)
                account_number = ""
                if tr.get("debtorAccount", {}):
                    account_number = tr.get("debtorAccount", {}).get("iban")
                if tr.get("creditorAccount", {}):
                    account_number = tr.get("creditorAccount", {}).get("iban")
                res.append(
                    {
                        "sequence": sequence,
                        "date": current_date,
                        "ref": re.sub(" +", " ", ref) or "/",
                        "payment_ref": tr.get("remittanceInformationUnstructured", ref),
                        "unique_import_id": tr.get("entryReference", False)
                        or tr.get("transactionId", False),
                        "amount": amount_currency,
                        "account_number": account_number,
                        "partner_name": partner_name,
                        "transaction_type": tr.get("bankTransactionCode", ""),
                        "narration": self._nordigen_get_note(tr),
                    }
                )
            return res
        except Exception as e:
            _logger.debug(
                _("Error getting requisition with %s: %s")
                % (self.nordigen_last_requisition_id, str(e))
            )
        return []

    def _get_nordigen_url_action(self):
        action_id = self.env.ref(
            "account_statement_import_online.online_bank_statement_provider_action"
        ).id
        params = {
            "action": action_id,
            "view_type": "form",
            "model": "online.bank.statement.provider",
            "id": self.id,
        }
        url = "/web#" + url_encode(params)
        return url

    def _nordigen_obtain_statement_data(self, date_since, date_until):
        if self.nordigen_account_id:
            new_transactions = self._nordigen_get_transactions(
                self.nordigen_account_id, date_since, date_until
            )
            if new_transactions:
                return new_transactions, {}
        else:
            url = self._get_nordigen_url_action()
            self.env.user.notify_danger(
                message=_(
                    "You should complete authorization process "
                    "for your bank account with Nordigen "
                    "<a href=%s>Click here</a> to complete "
                    "process in configuration page"
                )
                % url
            )
        return
