# Copyright 2020 Florent de Labarre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import base64
import json
import re
import time
from datetime import datetime

import pytz
import requests
from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from odoo.addons.base.models.res_bank import sanitize_account_number

PONTO_ENDPOINT = "https://api.myponto.com"


class OnlineBankStatementProviderPonto(models.Model):
    _inherit = "online.bank.statement.provider"

    ponto_token = fields.Char(readonly=True)
    ponto_token_expiration = fields.Datetime(readonly=True)
    ponto_last_identifier = fields.Char(readonly=True)

    def ponto_reset_last_identifier(self):
        self.write({"ponto_last_identifier": False})

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("ponto", "MyPonto.com"),
        ]

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "ponto":
            return super()._obtain_statement_data(date_since, date_until)
        return self._ponto_obtain_statement_data(date_since, date_until)

    #########
    # ponto #
    #########

    def _ponto_header_token(self):
        self.ensure_one()
        if self.username and self.password:
            login = "{}:{}".format(self.username, self.password)
            login = base64.b64encode(login.encode("UTF-8")).decode("UTF-8")
            return {
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
                "Authorization": "Basic %s" % login,
            }
        raise UserError(_("Please fill login and key."))

    def _ponto_header(self):
        self.ensure_one()
        if (
            not self.ponto_token
            or not self.ponto_token_expiration
            or self.ponto_token_expiration <= fields.Datetime.now()
        ):

            url = PONTO_ENDPOINT + "/oauth2/token"
            response = requests.post(
                url,
                params={"grant_type": "client_credentials"},
                headers=self._ponto_header_token(),
            )
            if response.status_code == 200:
                data = json.loads(response.text)
                access_token = data.get("access_token", False)
                if not access_token:
                    raise UserError(_("Ponto : no token"))
                else:
                    self.sudo().ponto_token = access_token
                    expiration_date = fields.Datetime.now() + relativedelta(
                        seconds=data.get("expires_in", False)
                    )
                    self.sudo().ponto_token_expiration = expiration_date
            else:
                raise UserError(
                    _("{} \n\n {}").format(response.status_code, response.text)
                )
        return {
            "Accept": "application/json",
            "Authorization": "Bearer %s" % self.ponto_token,
        }

    def _ponto_get_account_ids(self):
        url = PONTO_ENDPOINT + "/accounts"
        response = requests.get(
            url, params={"limit": 100}, headers=self._ponto_header()
        )
        if response.status_code == 200:
            data = json.loads(response.text)
            res = {}
            for account in data.get("data", []):
                iban = sanitize_account_number(
                    account.get("attributes", {}).get("reference", "")
                )
                res[iban] = account.get("id")
            return res
        raise UserError(_("{} \n\n {}").format(response.status_code, response.text))

    def _ponto_synchronisation(self, account_id):
        url = PONTO_ENDPOINT + "/synchronizations"
        data = {
            "data": {
                "type": "synchronization",
                "attributes": {
                    "resourceType": "account",
                    "resourceId": account_id,
                    "subtype": "accountTransactions",
                },
            }
        }
        response = requests.post(url, headers=self._ponto_header(), json=data)
        if response.status_code in (200, 201, 400):
            data = json.loads(response.text)
            sync_id = data.get("attributes", {}).get("resourceId", False)
        else:
            raise UserError(
                _("Error during Create Synchronisation {} \n\n {}").format(
                    response.status_code, response.text
                )
            )

        # Check synchronisation
        if not sync_id:
            return
        url = PONTO_ENDPOINT + "/synchronizations/" + sync_id
        number = 0
        while number == 100:
            number += 1
            response = requests.get(url, headers=self._ponto_header())
            if response.status_code == 200:
                data = json.loads(response.text)
                status = data.get("status", {})
                if status in ("success", "error"):
                    return
            time.sleep(4)

    def _ponto_get_transaction(self, account_id, date_since, date_until):
        page_url = PONTO_ENDPOINT + "/accounts/" + account_id + "/transactions"
        params = {"limit": 100}
        page_next = True
        last_identifier = self.ponto_last_identifier
        if last_identifier:
            params["before"] = last_identifier
            page_next = False
        transaction_lines = []
        latest_identifier = False
        while page_url:
            response = requests.get(
                page_url, params=params, headers=self._ponto_header()
            )
            if response.status_code != 200:
                raise UserError(
                    _("Error during get transaction.\n\n{} \n\n {}").format(
                        response.status_code, response.text
                    )
                )
            if params.get("before"):
                params.pop("before")
            data = json.loads(response.text)
            links = data.get("links", {})
            if page_next:
                page_url = links.get("next", False)
            else:
                page_url = links.get("prev", False)
            transactions = data.get("data", [])
            if transactions:
                current_transactions = []
                for transaction in transactions:
                    date = self._ponto_date_from_string(
                        transaction.get("attributes", {}).get("executionDate")
                    )
                    if date_since <= date < date_until:
                        current_transactions.append(transaction)
                if current_transactions:
                    if not page_next or (page_next and not latest_identifier):
                        latest_identifier = current_transactions[0].get("id")
                    transaction_lines.extend(current_transactions)
        if latest_identifier:
            self.ponto_last_identifier = latest_identifier
        return transaction_lines

    def _ponto_date_from_string(self, date_str):
        """Dates in Ponto are expressed in UTC, so we need to convert them
        to supplied tz for proper classification.
        """
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.tz or "utc"))
        return dt.replace(tzinfo=None)

    def _ponto_obtain_statement_data(self, date_since, date_until):
        """Translate information from Ponto to Odoo bank statement lines."""
        self.ensure_one()
        account_ids = self._ponto_get_account_ids()
        journal = self.journal_id
        iban = self.account_number
        account_id = account_ids.get(iban)
        if not account_id:
            raise UserError(
                _("Ponto : wrong configuration, unknow account %s")
                % journal.bank_account_id.acc_number
            )
        self._ponto_synchronisation(account_id)
        transaction_lines = self._ponto_get_transaction(
            account_id, date_since, date_until
        )
        new_transactions = []
        sequence = 0
        for transaction in transaction_lines:
            sequence += 1
            vals_line = self._ponto_get_transaction_vals(transaction, sequence)
            new_transactions.append(vals_line)
        if new_transactions:
            return new_transactions, {}
        return

    def _ponto_get_transaction_vals(self, transaction, sequence):
        """Translate information from Ponto to statement line vals."""
        attributes = transaction.get("attributes", {})
        ref_list = [
            attributes.get(x)
            for x in {"description", "counterpartName", "counterpartReference"}
            if attributes.get(x)
        ]
        ref = " ".join(ref_list)
        date = self._ponto_date_from_string(attributes.get("executionDate"))
        vals_line = {
            "sequence": sequence,
            "date": date,
            "ref": re.sub(" +", " ", ref) or "/",
            "payment_ref": attributes.get("remittanceInformation", ref),
            "unique_import_id": transaction["id"],
            "amount": attributes["amount"],
            "online_raw_data": transaction,
        }
        if attributes.get("counterpartReference"):
            vals_line["account_number"] = attributes["counterpartReference"]
        if attributes.get("counterpartName"):
            vals_line["partner_name"] = attributes["counterpartName"]
        return vals_line
