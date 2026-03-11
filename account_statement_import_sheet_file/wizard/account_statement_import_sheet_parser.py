# Copyright 2019 ForgeFlow, S.L.
# Copyright 2020 CorporateHub (https://corporatehub.eu)
# Copyright 2025 Jacques-Etienne Baudoux (BCIM) <je@bcim.be>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import itertools
import logging
import math
import re
from collections.abc import Iterable
from datetime import datetime
from decimal import Decimal
from io import StringIO
from os import path

from odoo import api, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

try:
    from csv import reader

    import xlrd
    from xlrd.xldate import xldate_as_datetime
except (OSError, ImportError) as err:  # pragma: no cover
    _logger.error(err)

try:
    import chardet
except ImportError:
    _logger.warning(
        "chardet library not found, please install it "
        "from http://pypi.python.org/pypi/chardet"
    )


class AccountStatementImportSheetParser(models.TransientModel):
    _name = "account.statement.import.sheet.parser"
    _description = "Bank Statement Import Sheet Parser"

    @api.model
    def parse_header(self, csv_or_xlsx, mapping):
        if mapping.no_header:
            return []
        header_line = mapping.header_lines_skip_count
        # prevent negative indexes
        if header_line > 0:
            header_line -= 1
        if isinstance(csv_or_xlsx, tuple):
            header = [
                str(value).strip() for value in csv_or_xlsx[1].row_values(header_line)
            ]
        else:
            [next(csv_or_xlsx) for _i in range(header_line)]
            header = [value.strip() for value in next(csv_or_xlsx)]
        if mapping.offset_column:
            header = header[mapping.offset_column :]
        return header

    @api.model
    def parse(self, data_file, mapping, filename):
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
            "name": self.env._(
                "%(code)s: %(filename)s",
                code=journal.code,
                filename=path.basename(filename),
            ),
        }

        if mapping.balance_column:
            balance_start = first_line["balance"]
            balance_start -= first_line["amount"]
            balance_end = last_line["balance"]
            data.update(
                {
                    "balance_start": balance_start,
                    "balance_end_real": balance_end,
                }
            )
        transactions = list(
            itertools.chain.from_iterable(
                map(lambda line: self._convert_line_to_transactions(line), lines)
            )
        )
        data.update({"transactions": transactions})

        return currency_code, account_number, [data]

    def _get_column_indexes(self, header, column_name, mapping):
        column_indexes = []
        if (
            mapping[column_name]
            and isinstance(mapping[column_name], Iterable)
            and "," in mapping[column_name]
        ):
            # We have to concatenate the values
            column_names_or_indexes = mapping[column_name].split(",")
        else:
            column_names_or_indexes = [mapping[column_name]]
        for column_name_or_index in column_names_or_indexes:
            if not column_name_or_index:
                continue
            column_index = None
            if mapping.no_header:
                try:
                    column_index = int(column_name_or_index)
                # pylint: disable=except-pass
                except Exception:
                    pass
                if column_index is not None:
                    column_indexes.append(column_index)
            else:
                if column_name_or_index:
                    column_indexes.append(header.index(column_name_or_index))
        return column_indexes

    def _get_column_names(self):
        return [
            "timestamp_column",
            "currency_column",
            "amount_column",
            "amount_debit_column",
            "amount_credit_column",
            "balance_column",
            "original_currency_column",
            "original_amount_column",
            "debit_credit_column",
            "transaction_id_column",
            "description_column",
            "notes_column",
            "reference_column",
            "partner_name_column",
            "bank_name_column",
            "bank_account_column",
        ]

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
            try:
                decoded_file = data_file.decode(mapping.file_encoding or "utf-8")
            except UnicodeDecodeError:
                # Try auto guessing the format
                detected_encoding = chardet.detect(data_file).get("encoding", False)
                if not detected_encoding:
                    raise UserError(
                        self.env._("No valid encoding was found for the attached file")
                    ) from None
                decoded_file = data_file.decode(detected_encoding)
            csv_or_xlsx = reader(StringIO(decoded_file), **csv_options)
        header = self.parse_header(csv_or_xlsx, mapping)

        # NOTE no seria necesario debit_column y credit_column ya que tenemos los
        # respectivos campos related
        for column_name in self._get_column_names():
            columns[column_name] = self._get_column_indexes(
                header, column_name, mapping
            )

        # Get the numbers of rows of the file
        if isinstance(csv_or_xlsx, tuple):
            numrows = csv_or_xlsx[1].nrows
        else:
            numrows = len(str(data_file.strip()).split("\\n"))

        label_line = mapping.header_lines_skip_count
        footer_line = numrows - mapping.footer_lines_skip_count

        if isinstance(csv_or_xlsx, tuple):
            rows = range(label_line, footer_line)
        else:
            rows = csv_or_xlsx
        data = csv_or_xlsx, rows, label_line, footer_line
        return self._parse_rows(mapping, currency_code, data, columns)

    def _get_values_from_column(self, values, columns, column_name):
        if not columns[column_name]:
            return None
        indexes = columns[column_name]
        content_l = []
        max_index = len(values) - 1
        for index in indexes:
            if isinstance(index, int):
                if index <= max_index:
                    content_l.append(values[index])
            else:
                if index in values:
                    content_l.append(values[index])
        if all(isinstance(content, str) for content in content_l):
            return " ".join(content_l)
        return content_l[0]

    def _parse_one_line(self, mapping, currency_code, values, columns):  # noqa: C901
        # Get all the raw values from the columns processed in one dict, and extract
        # the ones we need to process in order to use less variables in the rest of
        # the method
        raw_values = {}
        for column in self._get_column_names():
            raw_values[column] = self._get_values_from_column(values, columns, column)

        timestamp = raw_values["timestamp_column"]
        currency = raw_values["currency_column"] or currency_code

        if currency != currency_code:
            return None

        def _decimal(column_name):
            if columns[column_name]:
                return self._parse_decimal(raw_values[column_name], mapping)
            return None

        amount = _decimal("amount_column")
        if not amount:
            amount = abs(_decimal("amount_debit_column") or 0)
        if not amount:
            amount = -abs(_decimal("amount_credit_column") or 0)

        balance = raw_values["balance_column"]
        original_amount = raw_values["original_amount_column"]
        debit_credit = raw_values["debit_credit_column"]
        debit_column = raw_values["amount_debit_column"]
        credit_column = raw_values["amount_credit_column"]

        if isinstance(timestamp, str):
            timestamp = datetime.strptime(timestamp, mapping.timestamp_format)
            if timestamp.year == 1900:
                # No year indicated, so put the current or previous one depending
                # on the current month (i.e. in January, importing December)
                now = datetime.now()
                year = now.year
                if timestamp.month > now.month:
                    year -= 1
                timestamp = timestamp.replace(year=year)

        if balance:
            balance = self._parse_decimal(balance, mapping)
        else:
            balance = None

        if debit_credit is not None:
            amount = abs(amount)
            if debit_credit == mapping.debit_value:
                amount = -amount

        if debit_column and credit_column:
            debit_amount = self._parse_decimal(debit_column, mapping)
            debit_amount = abs(debit_amount)
            credit_amount = self._parse_decimal(credit_column, mapping)
            credit_amount = abs(credit_amount)
            amount = -(credit_amount - debit_amount)

        if original_amount:
            original_amount = math.copysign(
                self._parse_decimal(original_amount, mapping), amount
            )
        else:
            original_amount = 0.0
        if mapping.amount_inverse_sign:
            amount = -amount
            original_amount = -original_amount
            balance = -balance if balance is not None else balance
        line = {
            "timestamp": timestamp,
            "amount": amount,
            "currency": currency,
            "original_amount": original_amount,
            "original_currency": raw_values["original_currency_column"],
        }

        def _update_line(column_name, value):
            if value is not None:
                line[column_name] = value

        # Update line with the rest of the values if they are not None
        _update_line("balance", balance)
        _update_line("transaction_id", raw_values["transaction_id_column"])
        _update_line("description", raw_values["description_column"])
        _update_line("notes", raw_values["notes_column"])
        _update_line("reference", raw_values["reference_column"])
        _update_line("partner_name", raw_values["partner_name_column"])
        _update_line("bank_name", raw_values["bank_name_column"])
        _update_line("bank_account", raw_values["bank_account_column"])
        return line

    def _parse_rows(self, mapping, currency_code, data, columns):
        csv_or_xlsx, rows, label_line, footer_line = data

        lines = []
        for index, row in enumerate(rows, label_line):
            if isinstance(csv_or_xlsx, tuple):
                book = csv_or_xlsx[0]
                sheet = csv_or_xlsx[1]
                values = []
                for col_index in range(mapping.offset_column, sheet.row_len(row)):
                    cell_type = sheet.cell_type(row, col_index)
                    cell_value = sheet.cell_value(row, col_index)
                    if cell_type == xlrd.XL_CELL_DATE:
                        cell_value = xldate_as_datetime(cell_value, book.datemode)
                    values.append(cell_value)
            else:
                if index >= footer_line:
                    continue
                values = list(row)
            if mapping.skip_empty_lines and not any(values):
                continue

            line = self._parse_one_line(mapping, currency_code, values, columns)
            if line:
                lines.append(line)
        return lines

    @api.model
    def _convert_line_to_transactions(self, line):  # noqa: C901
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

        if original_currency == currency:
            original_currency = None
            if not amount:
                amount = original_amount
            original_amount = "0.0"

        def _update_currency(column_name, value):
            if value:
                currency = self.env["res.currency"].search(
                    [("name", "=", value)],
                    limit=1,
                )
                if currency:
                    transaction[column_name] = currency.id

        _update_currency("currency_id", currency)
        _update_currency("foreign_currency_id", original_currency)

        if original_amount:
            transaction["amount_currency"] = str(original_amount)

        if transaction_id:
            transaction["unique_import_id"] = (
                f"{transaction_id}-{int(timestamp.timestamp())}"
            )

        transaction["payment_ref"] = description or self.env._("N/A")
        if reference:
            transaction["ref"] = reference

        note = ""
        if bank_name:
            note += self.env._("Bank: %s; ", bank_name)
        if bank_account:
            note += self.env._("Account: %s; ", bank_account)
        if transaction_id:
            note += self.env._("Transaction ID: %s; ", transaction_id)
        if note and notes:
            note = f"{notes}\n{note.strip()}"
        elif note:
            note = note.strip()
        elif notes:
            note = notes
        if note:
            transaction["narration"] = note

        if partner_name:
            transaction["partner_name"] = partner_name
        if bank_account:
            transaction["account_number"] = bank_account

        return [transaction]

    @api.model
    def _parse_decimal(self, value, mapping):
        if isinstance(value, Decimal):
            return float(value)
        elif isinstance(value, float):
            return value
        thousands, decimal = mapping._get_float_separators()
        # Remove all characters except digits, thousands separator,
        # decimal separator, and signs
        value = (
            re.sub(
                r"[^\d\-+" + re.escape(thousands) + re.escape(decimal) + "]+", "", value
            )
            or "0"
        )
        value = value.replace(thousands, "")
        float_separator = "."
        if decimal:
            value = value.replace(decimal, float_separator)
        else:
            journal = self.env["account.journal"].browse(
                self.env.context.get("journal_id")
            )
            currency = journal.currency_id or journal.company_id.currency_id
            decimal_places = currency.decimal_places if currency else 2
            value = value[:-decimal_places] + float_separator + value[-decimal_places:]
        return float(value)
