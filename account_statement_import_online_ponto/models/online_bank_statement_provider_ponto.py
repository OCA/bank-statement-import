# Copyright 2020 Florent de Labarre
# Copyright 2022-2023 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
import json
import logging
import re
from datetime import datetime

import pytz

from odoo import _, api, fields, models

_logger = logging.getLogger(__name__)


class OnlineBankStatementProviderPonto(models.Model):
    _inherit = "online.bank.statement.provider"

    ponto_date_field = fields.Selection(
        [
            ("execution_date", "Execution Date"),
            ("value_date", "Value Date"),
        ],
        string="Ponto Date Field",
        default="execution_date",
        help="Select the Ponto date field that will be used for "
        "the Odoo bank statement line date. If you change this parameter "
        "on a provider that already has transactions, you will have to "
        "purge the Ponto buffers.",
    )

    @api.model
    def _get_available_services(self):
        """Each provider model must register its service."""
        return super()._get_available_services() + [
            ("ponto", "MyPonto.com"),
        ]

    def _obtain_statement_data(self, date_since, date_until):
        """Check wether called for ponto servide, otherwise pass the buck."""
        self.ensure_one()
        if self.service != "ponto":  # pragma: no cover
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
            date_until,
        )
        lines = self._ponto_retrieve_data(date_since)
        new_transactions = []
        sequence = 0
        for transaction in lines:
            date = self._ponto_get_transaction_datetime(transaction)
            if date < date_since or date > date_until:
                continue
            sequence += 1
            vals_line = self._ponto_get_transaction_vals(transaction, sequence)
            new_transactions.append(vals_line)
        return new_transactions, {}

    def _ponto_retrieve_data(self, date_since):
        """Fill buffer with data from Ponto.

        We will retrieve data from the latest transactions present in Ponto
        backwards, until we find data that has an execution date before date_since.
        """
        lines = []
        interface_model = self.env["ponto.interface"]
        access_data = interface_model._login(self.username, self.password)
        interface_model._set_access_account(access_data, self.account_number)
        latest_identifier = False
        transactions = interface_model._get_transactions(access_data, latest_identifier)
        while transactions:
            lines.extend(transactions)
            latest_identifier = transactions[-1].get("id")
            earliest_datetime = self._ponto_get_transaction_datetime(transactions[-1])
            if earliest_datetime < date_since:
                break
            transactions = interface_model._get_transactions(
                access_data, latest_identifier
            )
        return lines

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
        date = self._ponto_get_transaction_datetime(transaction)
        vals_line = {
            "sequence": sequence,
            "date": date,
            "ref": re.sub(" +", " ", ref) or "/",
            "payment_ref": attributes.get("remittanceInformation", ref),
            "unique_import_id": transaction["id"],
            "amount": attributes["amount"],
            "raw_data": json.dumps(transaction),
        }
        if attributes.get("counterpartReference"):
            vals_line["account_number"] = attributes["counterpartReference"]
        if attributes.get("counterpartName"):
            vals_line["partner_name"] = attributes["counterpartName"]
        return vals_line

    def _ponto_get_transaction_datetime(self, transaction):
        """Get execution datetime for a transaction.

        Odoo often names variables containing date and time just xxx_date or
        date_xxx. We try to avoid this misleading naming by using datetime as
        much for variables and fields of type datetime.
        """
        attributes = transaction.get("attributes", {})
        if self.ponto_date_field == "value_date":
            datetime_str = attributes.get("valueDate")
        else:
            datetime_str = attributes.get("executionDate")
        return self._ponto_datetime_from_string(datetime_str)

    def _ponto_datetime_from_string(self, datetime_str):
        """Dates in Ponto are expressed in UTC, so we need to convert them
        to supplied tz for proper classification.
        """
        dt = datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.tz or "utc"))
        return dt.replace(tzinfo=None)
