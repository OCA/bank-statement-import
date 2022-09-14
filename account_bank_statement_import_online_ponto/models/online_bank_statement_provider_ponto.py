# Copyright 2020 Florent de Labarre
# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
from datetime import date, datetime
from dateutil.relativedelta import relativedelta
import json
import pytz

import logging
import re

from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)


class OnlineBankStatementProviderPonto(models.Model):
    _inherit = "online.bank.statement.provider"

    ponto_buffer_retain_days = fields.Integer(
        string="Number of days to keep Ponto Buffers",
        default=61,
        help="By default buffers will be kept for 61 days.\n"
        "Set this to 0 to keep buffers indefinitely.",
    )

    @api.model
    def _get_available_services(self):
        return super()._get_available_services() + [
            ("ponto", "MyPonto.com"),
        ]

    @api.multi
    def _pull(self, date_since, date_until):
        """Override pull to first retrieve data from Ponto."""
        if self.service == "ponto":
            self._ponto_retrieve_data(date_since)
        super()._pull(date_since, date_until)

    def _ponto_retrieve_data(self, date_since):
        """Fill buffer with data from Ponto.

        We will retrieve data from the latest transactions present in Ponto
        backwards, until we find data that has an execution date before date_since.
        """
        interface_model = self.env["ponto.interface"]
        buffer_model = self.env["ponto.buffer"]
        access_data = interface_model._login(self.username, self.password)
        interface_model._set_access_account(access_data, self.account_number)
        interface_model._ponto_synchronisation(access_data)
        latest_identifier = False
        transactions = interface_model._get_transactions(
            access_data,
            latest_identifier
        )
        while transactions:
            buffer_model.sudo()._store_transactions(self, transactions)
            latest_identifier = transactions[-1].get("id")
            earliest_datetime = self._ponto_get_execution_datetime(transactions[-1])
            if earliest_datetime < date_since:
                break
            transactions = interface_model._get_transactions(
                access_data,
                latest_identifier
            )

    def _obtain_statement_data(self, date_since, date_until):
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
        return new_transactions, {}

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
        date = self._ponto_get_execution_datetime(transaction)
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

    def _ponto_get_execution_datetime(self, transaction):
        """Get execution datetime for a transaction.

        Odoo often names variables containing date and time just xxx_date or
        date_xxx. We try to avoid this misleading naming by using datetime as
        much for variables and fields of type datetime.
        """
        attributes = transaction.get("attributes", {})
        return self._ponto_datetime_from_string(attributes.get("executionDate"))

    def _ponto_datetime_from_string(self, date_str):
        """Dates in Ponto are expressed in UTC, so we need to convert them
        to supplied tz for proper classification.
        """
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        dt = dt.replace(tzinfo=pytz.utc).astimezone(pytz.timezone(self.tz or "utc"))
        return dt.replace(tzinfo=None)

    def _ponto_buffer_purge(self):
        """Remove buffers from Ponto no longer needed to import statements."""
        _logger.info("Scheduled purge of old ponto buffers...")
        today = date.today()
        buffer_model = self.env["ponto.buffer"]
        providers = self.search([
            ("active", "=", True),
        ])
        for provider in providers:
            if provider.service != "ponto":
                continue
            if not provider.ponto_buffer_retain_days:
                continue
            cutoff_date = today - relativedelta(days=provider.ponto_buffer_retain_days)
            old_buffers = buffer_model.search(
                [
                    ("provider_id", "=", provider.id),
                    ("effective_date", "<", cutoff_date),
                ]
            )
            old_buffers.unlink()
        _logger.info("Scheduled purge of old ponto buffers complete.")
