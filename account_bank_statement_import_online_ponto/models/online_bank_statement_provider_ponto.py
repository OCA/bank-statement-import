# Copyright 2020 Florent de Labarre
# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import datetime
import json
import pytz

import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class OnlineBankStatementProviderPonto(models.Model):
    _inherit = "online.bank.statement.provider"

    ponto_last_identifier = fields.Char(readonly=True)

    def ponto_reset_last_identifier(self):
        self.write({"ponto_last_identifier": False})

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("ponto", "MyPonto.com"),
        ]

    @api.multi
    def _pull(self, date_since, date_until):
        """Override pull to first retrieve data from Ponto."""
        if self.service == "ponto":
            self._ponto_retrieve_data()
        super()._pull(date_since, date_until)

    def _ponto_retrieve_data(self):
        """Fill buffer with data from Ponto."""
        interface_model = self.env["ponto.interface"]
        buffer_model = self.env["ponto.buffer"]
        access_data = interface_model._login(self.username, self.password)
        interface_model._set_access_account(access_data, self.account_number)
        interface_model._ponto_synchronisation(access_data)
        latest_identifier = self.ponto_last_identifier
        transactions = interface_model._get_transactions(
            access_data,
            latest_identifier
        )
        while transactions:
            buffer_model.sudo()._store_transactions(self, transactions)
            latest_identifier = transactions[-1].get("id")
            transactions = interface_model._get_transactions(
                access_data,
                latest_identifier
            )
        self.ponto_last_identifier = latest_identifier

    def _obtain_statement_data(self, date_since, date_until):
        self.ensure_one()
        if self.service != "ponto":
            return super()._obtain_statement_data(
                date_since,
                date_until,
            )
        return self._ponto_obtain_statement_data(date_since, date_until)

    def _ponto_obtain_statement_data(self, date_since, date_until):
        """Translate information from Ponto to Odoo bank statement lines."""
        self.ensure_one()
        _logger.debug(
            _("Ponto obtain statement data for journal %s from %s to %s"),
            self.journal_id.name,
            date_since,
            date_until
        )
        line_model = self.env["ponto.buffer.line"]
        lines = line_model.sudo().search(
            [
                ("buffer_id.provider_id", "=", self.id),
                ("effective_date_time", ">=", date_since),
                ("effective_date_time", "<=", date_until),
            ]
        )
        new_transactions = []
        sequence = 0
        for transaction in lines:
            sequence += 1
            vals_line = self._ponto_get_transaction_vals(
                json.loads(transaction.transaction_data),
                sequence
            )
            new_transactions.append(vals_line)
        if new_transactions:
            return new_transactions, {}
        return

    def _ponto_get_transaction_vals(self, transaction, sequence):
        """Translate information from Ponto to statement line vals."""
        attributes = transaction.get("attributes", {})
        ref_list = [
            attributes.get(x)
            for x in {
                "description",
                "counterpartName",
                "counterpartReference",
            }
            if attributes.get(x)
        ]
        ref = " ".join(ref_list)
        date = self._ponto_date_from_string(attributes.get("executionDate"))
        vals_line = {
            "sequence": sequence,
            "date": date,
            "ref": re.sub(" +", " ", ref) or "/",
            "name": attributes.get("remittanceInformation") or ref,
            "unique_import_id": transaction["id"],
            "amount": attributes["amount"],
        }
        if attributes.get("counterpartReference"):
            vals_line["account_number"] = attributes["counterpartReference"]
        if attributes.get("counterpartName"):
            vals_line["partner_name"] = attributes["counterpartName"]
        return vals_line

    def _ponto_date_from_string(self, date_str):
        """Dates in Ponto are expressed in UTC, so we need to convert them
        to supplied tz for proper classification.
        """
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.tz or "utc"))
        return dt.replace(tzinfo=None)
