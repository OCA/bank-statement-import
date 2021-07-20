# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging
from datetime import datetime
from decimal import Decimal
from io import StringIO
from os import path

from pytz import timezone, utc

from odoo import _, api, models

_logger = logging.getLogger(__name__)

try:
    from csv import reader
except (ImportError, IOError) as err:
    _logger.error(err)


class AccountBankStatementImportPayPalParser(models.TransientModel):
    _name = "account.statement.import.paypal.parser"
    _description = "Account Statement Import PayPal Parser"

    @api.model
    def parse_header(self, data_file):
        data = StringIO(data_file.decode("utf-8-sig"))
        csv_data = reader(data)
        return list(next(csv_data))

    @api.model
    def parse(self, mapping, data_file, filename):
        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))
        currency_code = (journal.currency_id or journal.company_id.currency_id).name
        account_number = journal.bank_account_id.acc_number

        name = _("%s: %s") % (
            journal.code,
            path.basename(filename),
        )
        lines = self._parse_lines(mapping, data_file, currency_code)
        if not lines:
            return currency_code, account_number, [{"name": name, "transactions": []}]

        lines = list(sorted(lines, key=lambda line: line["timestamp"]))
        first_line = lines[0]
        balance_start = first_line["balance_amount"]
        balance_start -= first_line["gross_amount"]
        balance_start -= first_line["fee_amount"]
        last_line = lines[-1]
        balance_end = last_line["balance_amount"]

        transactions = list(
            itertools.chain.from_iterable(
                map(lambda line: self._convert_line_to_transactions(line), lines)
            )
        )

        return (
            currency_code,
            account_number,
            [
                {
                    "name": name,
                    "date": first_line["timestamp"].date(),
                    "balance_start": float(balance_start),
                    "balance_end_real": float(balance_end),
                    "transactions": transactions,
                }
            ],
        )

    def _data_dict_constructor(self, mapping, header):
        required_list = [
            "date_column",
            "time_column",
            "tz_column",
            "name_column",
            "currency_column",
            "gross_column",
            "fee_column",
            "balance_column",
            "transaction_id_column",
        ]
        optional_list = [
            "description_column",
            "type_column",
            "from_email_address_column",
            "to_email_address_column",
            "invoice_id_column",
            "subject_column",
            "note_column",
            "bank_name_column",
            "bank_account_column",
        ]
        data_dict = {}
        for key in required_list:
            data_dict[key] = header.index(getattr(mapping, key))
        for key in optional_list:
            try:
                data_dict[key] = header.index(getattr(mapping, key))
            except ValueError:
                data_dict[key] = None
        return data_dict

    def _parse_lines(self, mapping, data_file, currency_code):
        data = StringIO(data_file.decode("utf-8-sig"))
        csv_data = reader(data)

        header = list(next(csv_data))
        data_dict = self._data_dict_constructor(mapping, header)

        return self._calculate_lines(csv_data, data_dict, mapping, currency_code)

    def _calculate_lines(self, csv_data, data_dict, mapping, currency_code):
        lines = []
        for row in csv_data:
            row = list(row)
            dict_values = {}
            for key in data_dict:
                dict_values[key] = (
                    row[data_dict.get(key)] if data_dict.get(key) is not None else None
                )
            if dict_values.get("currency_column") != currency_code:
                continue

            date = datetime.strptime(
                dict_values.get("date_column"), mapping.date_format
            ).date()
            time = datetime.strptime(
                dict_values.get("time_column"), mapping.time_format
            ).time()
            timestamp = datetime.combine(date, time)
            tz_value = self._normalize_tz(dict_values.get("tz_column"))
            tz = timezone(tz_value)
            timestamp = timestamp.replace(tzinfo=tz)
            timestamp = timestamp.astimezone(utc).replace(tzinfo=None)
            gross_amount = self._parse_decimal(dict_values.get("gross_column"), mapping)
            fee_amount = self._parse_decimal(dict_values.get("fee_column"), mapping)
            balance_amount = self._parse_decimal(
                dict_values.get("balance_column"), mapping
            )
            bank = (
                "{} - {}".format(
                    dict_values.get("bank_name_column"),
                    dict_values.get("bank_account_column"),
                )
                if dict_values.get("bank_name_column")
                and dict_values.get("bank_account_column")
                else None
            )
            if data_dict.get("to_email_address_column") is None:
                payer_email = dict_values.get("from_email_address_column")
            else:
                payer_email = (
                    dict_values.get("to_email_address_column")
                    if gross_amount < 0.0
                    else dict_values.get("from_email_address_column")
                )

            lines.append(
                {
                    "transaction_id": dict_values.get("transaction_id_column"),
                    "invoice": dict_values.get("invoice_id_column"),
                    "description": dict_values.get("description_column")
                    or dict_values.get("type_column"),
                    "details": dict_values.get("subject_column")
                    or dict_values.get("note_column")
                    or bank,
                    "timestamp": timestamp,
                    "gross_amount": gross_amount,
                    "fee_amount": fee_amount,
                    "balance_amount": balance_amount,
                    "payer_name": dict_values.get("name_column"),
                    "payer_email": payer_email,
                    "partner_bank_name": dict_values.get("bank_name_column"),
                    "partner_bank_account": dict_values.get("bank_account_column"),
                }
            )
        return lines

    @api.model
    def _convert_line_to_transactions(self, line):
        transactions = []

        transaction_id = line["transaction_id"]
        invoice = line["invoice"]
        description = line["description"]
        details = line["details"]
        timestamp = line["timestamp"]
        gross_amount = line["gross_amount"]
        fee_amount = line["fee_amount"]
        payer_name = line["payer_name"]
        payer_email = line["payer_email"]
        partner_bank_account = line["partner_bank_account"]

        if invoice:
            invoice = _("Invoice %s") % invoice
        note = "{} {}".format(description, transaction_id)
        if details:
            note += ": %s" % details
        if payer_email:
            note += " (%s)" % payer_email

        unique_import_id = "{}-{}".format(transaction_id, int(timestamp.timestamp()))
        name = (invoice or details or description or "",)
        transaction = {
            "name": invoice or details or description or "",
            "amount": str(gross_amount),
            "date": timestamp,
            "payment_ref": note,
            "unique_import_id": unique_import_id,
        }
        if payer_name:
            line.update({"partner_name": payer_name})
        if partner_bank_account:
            line.update({"account_number": partner_bank_account})
        transactions.append(transaction)

        if fee_amount:
            transactions.append(
                {
                    "name": _("Fee for %s") % (name or transaction_id),
                    "amount": str(fee_amount),
                    "date": timestamp,
                    "partner_name": "PayPal",
                    "unique_import_id": "%s-FEE" % unique_import_id,
                    "payment_ref": _("Transaction fee for %s") % note,
                }
            )
        return transactions

    @api.model
    def _parse_decimal(self, value, mapping):
        thousands, decimal = mapping._get_float_separators()
        value = value.replace(thousands, "")
        value = value.replace(decimal, ".")
        return Decimal(value)

    @api.model
    def _normalize_tz(self, value):
        if value in ["PDT", "PST"]:
            return "America/Los_Angeles"
        elif value in ["CET", "CEST"]:
            return "Europe/Paris"
        return value
