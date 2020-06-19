# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging
from datetime import datetime
from decimal import Decimal
from io import StringIO

from odoo import _, api, models

_logger = logging.getLogger(__name__)

try:
    from csv import reader
    import xlrd
    from xlrd.xldate import xldate_as_datetime
except (ImportError, IOError) as err:  # pragma: no cover
    _logger.error(err)


class AccountBankStatementImportSheetParser(models.TransientModel):
    _name = "account.bank.statement.import.sheet.parser"
    _description = "Account Bank Statement Import Sheet Parser"

    @api.model
    def parse_header(self, data_file, encoding, csv_options):
        try:
            workbook = xlrd.open_workbook(
                file_contents=data_file,
                encoding_override=encoding if encoding else None,
            )
            sheet = workbook.sheet_by_index(0)
            values = sheet.row_values(0)
            return [str(value) for value in values]
        except xlrd.XLRDError:
            pass

        data = StringIO(data_file.decode(encoding or "utf-8"))
        csv_data = reader(data, **csv_options)
        return list(next(csv_data))

    @api.model
    def parse(self, data_file, mapping):
        journal = self.env["account.journal"].browse(self.env.context.get("journal_id"))
        currency_code = (journal.currency_id or journal.company_id.currency_id).name
        account_number = journal.bank_account_id.acc_number

        lines = self._parse_lines(mapping, data_file, currency_code)
        if not lines:
            return currency_code, account_number, [{"transactions": []}]

        lines = list(sorted(lines, key=lambda line: line["timestamp"]))
        first_line = lines[0]
        last_line = lines[-1]
        data = {
            "date": first_line["timestamp"].date(),
        }

        if mapping.balance_column:
            balance_start = first_line["balance"]
            balance_start -= first_line["amount"]
            balance_end = last_line["balance"]
            data.update(
                {
                    "balance_start": float(balance_start),
                    "balance_end_real": float(balance_end),
                }
            )

        transactions = list(
            itertools.chain.from_iterable(
                map(lambda line: self._convert_line_to_transactions(line), lines)
            )
        )
        data.update({"transactions": transactions})

        return currency_code, account_number, [data]

    def _parse_lines(self, mapping, data_file, currency_code):
        columns = dict()
        try:
            workbook = xlrd.open_workbook(
                file_contents=data_file,
                encoding_override=(
                    mapping.file_encoding if mapping.file_encoding else None
                ),
            )
            csv_or_xlsx = (
                workbook,
                workbook.sheet_by_index(0),
            )
        except xlrd.XLRDError:
            csv_options = {}
            csv_delimiter = mapping._get_column_delimiter_character()
            if csv_delimiter:
                csv_options["delimiter"] = csv_delimiter
            if mapping.quotechar:
                csv_options["quotechar"] = mapping.quotechar
            csv_or_xlsx = reader(
                StringIO(data_file.decode(mapping.file_encoding or "utf-8")),
                **csv_options
            )

        if isinstance(csv_or_xlsx, tuple):
            header = [str(value) for value in csv_or_xlsx[1].row_values(0)]
        else:
            header = [value.strip() for value in next(csv_or_xlsx)]
        columns["timestamp_column"] = header.index(mapping.timestamp_column)
        columns["currency_column"] = (
            header.index(mapping.currency_column) if mapping.currency_column else None
        )
        columns["amount_column"] = header.index(mapping.amount_column)
        columns["balance_column"] = (
            header.index(mapping.balance_column) if mapping.balance_column else None
        )
        columns["original_currency_column"] = (
            header.index(mapping.original_currency_column)
            if mapping.original_currency_column
            else None
        )
        columns["original_amount_column"] = (
            header.index(mapping.original_amount_column)
            if mapping.original_amount_column
            else None
        )
        columns["debit_credit_column"] = (
            header.index(mapping.debit_credit_column)
            if mapping.debit_credit_column
            else None
        )
        columns["transaction_id_column"] = (
            header.index(mapping.transaction_id_column)
            if mapping.transaction_id_column
            else None
        )
        columns["description_column"] = (
            header.index(mapping.description_column)
            if mapping.description_column
            else None
        )
        columns["notes_column"] = (
            header.index(mapping.notes_column) if mapping.notes_column else None
        )
        columns["reference_column"] = (
            header.index(mapping.reference_column) if mapping.reference_column else None
        )
        columns["partner_name_column"] = (
            header.index(mapping.partner_name_column)
            if mapping.partner_name_column
            else None
        )
        columns["bank_name_column"] = (
            header.index(mapping.bank_name_column) if mapping.bank_name_column else None
        )
        columns["bank_account_column"] = (
            header.index(mapping.bank_account_column)
            if mapping.bank_account_column
            else None
        )
        return self._parse_rows(mapping, currency_code, csv_or_xlsx, columns)

    def _parse_rows(self, mapping, currency_code, csv_or_xlsx, columns):  # noqa: C901
        if isinstance(csv_or_xlsx, tuple):
            rows = range(1, csv_or_xlsx[1].nrows)
        else:
            rows = csv_or_xlsx

        lines = []
        for row in rows:
            if isinstance(csv_or_xlsx, tuple):
                book = csv_or_xlsx[0]
                sheet = csv_or_xlsx[1]
                values = []
                for col_index in range(sheet.row_len(row)):
                    cell_type = sheet.cell_type(row, col_index)
                    cell_value = sheet.cell_value(row, col_index)
                    if cell_type == xlrd.XL_CELL_DATE:
                        cell_value = xldate_as_datetime(cell_value, book.datemode)
                    values.append(cell_value)
            else:
                values = list(row)

            timestamp = values[columns["timestamp_column"]]
            currency = (
                values[columns["currency_column"]]
                if columns["currency_column"] is not None
                else currency_code
            )
            amount = values[columns["amount_column"]]
            balance = (
                values[columns["balance_column"]]
                if columns["balance_column"] is not None
                else None
            )
            original_currency = (
                values[columns["original_currency_column"]]
                if columns["original_currency_column"] is not None
                else None
            )
            original_amount = (
                values[columns["original_amount_column"]]
                if columns["original_amount_column"] is not None
                else None
            )
            debit_credit = (
                values[columns["debit_credit_column"]]
                if columns["debit_credit_column"] is not None
                else None
            )
            transaction_id = (
                values[columns["transaction_id_column"]]
                if columns["transaction_id_column"] is not None
                else None
            )
            description = (
                values[columns["description_column"]]
                if columns["description_column"] is not None
                else None
            )
            notes = (
                values[columns["notes_column"]]
                if columns["notes_column"] is not None
                else None
            )
            reference = (
                values[columns["reference_column"]]
                if columns["reference_column"] is not None
                else None
            )
            partner_name = (
                values[columns["partner_name_column"]]
                if columns["partner_name_column"] is not None
                else None
            )
            bank_name = (
                values[columns["bank_name_column"]]
                if columns["bank_name_column"] is not None
                else None
            )
            bank_account = (
                values[columns["bank_account_column"]]
                if columns["bank_account_column"] is not None
                else None
            )

            if currency != currency_code:
                continue

            if isinstance(timestamp, str):
                timestamp = datetime.strptime(timestamp, mapping.timestamp_format)

            amount = self._parse_decimal(amount, mapping)
            if balance is not None:
                balance = self._parse_decimal(balance, mapping)

            if debit_credit is not None:
                amount = amount.copy_abs()
                if debit_credit == mapping.debit_value:
                    amount = -amount

            if original_currency is None:
                original_currency = currency
                original_amount = amount
            elif original_currency == currency:
                original_amount = amount

            if original_amount is not None:
                original_amount = self._parse_decimal(original_amount, mapping)
            else:
                original_amount = 0.0

            line = {
                "timestamp": timestamp,
                "amount": amount,
                "currency": currency,
                "original_amount": original_amount,
                "original_currency": original_currency,
            }
            if balance is not None:
                line["balance"] = balance
            if transaction_id is not None:
                line["transaction_id"] = transaction_id
            if description is not None:
                line["description"] = description
            if notes is not None:
                line["notes"] = notes
            if reference is not None:
                line["reference"] = reference
            if partner_name is not None:
                line["partner_name"] = partner_name
            if bank_name is not None:
                line["bank_name"] = bank_name
            if bank_account is not None:
                line["bank_account"] = bank_account
            lines.append(line)
        return lines

    @api.model
    def _convert_line_to_transactions(self, line):
        """Hook for extension"""
        timestamp = line["timestamp"]
        amount = line["amount"]
        currency = line["currency"]
        original_amount = line["original_amount"]
        original_currency = line["original_currency"]
        transaction_id = line.get("transaction_id")
        description = line.get("description")
        notes = line.get("notes")
        reference = line.get("reference")
        partner_name = line.get("partner_name")
        bank_name = line.get("bank_name")
        bank_account = line.get("bank_account")

        transaction = {
            "date": timestamp,
            "amount": str(amount),
        }
        if currency != original_currency:
            original_currency = self.env["res.currency"].search(
                [("name", "=", original_currency)], limit=1,
            )
            if original_currency:
                transaction.update(
                    {
                        "amount_currency": str(original_amount),
                        "currency_id": original_currency.id,
                    }
                )

        if transaction_id:
            transaction["unique_import_id"] = "{}-{}".format(
                transaction_id, int(timestamp.timestamp()),
            )

        transaction["name"] = description or _("N/A")
        if reference:
            transaction["ref"] = reference

        note = ""
        if bank_name:
            note += _("Bank: %s; ") % (bank_name,)
        if bank_account:
            note += _("Account: %s; ") % (bank_account,)
        if transaction_id:
            note += _("Transaction ID: %s; ") % (transaction_id,)
        if note and notes:
            note = "{}\n{}".format(note, note.strip())
        elif note:
            note = note.strip()
        if note:
            transaction["note"] = note

        if partner_name:
            transaction["partner_name"] = partner_name
        if bank_account:
            transaction["account_number"] = bank_account

        return [transaction]

    @api.model
    def _parse_decimal(self, value, mapping):
        if isinstance(value, Decimal):
            return value
        elif isinstance(value, float):
            return Decimal(value)
        thousands, decimal = mapping._get_float_separators()
        value = value.replace(thousands, "")
        value = value.replace(decimal, ".")
        return Decimal(value)
