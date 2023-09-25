# Copyright 2017 Opener BV (<https://opener.amsterdam>)
# Copyright 2021-2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
"""Add import of Adyen statements."""
# pylint: disable=protected-access,no-self-use
import logging

from odoo import _, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)  # pylint: disable=invalid-name

COLUMNS = {
    "Company Account": 1,
    "Merchant Account": 2,
    "Psp Reference": 3,
    "Merchant Reference": 4,
    "Payment Method": 5,  # Not used at present
    "Creation Date": 6,
    "TimeZone": 7,  # Not used at present
    "Type": 8,
    "Modification Reference": 9,
    "Gross Currency": 10,  # Not used at present
    "Gross Debit (GC)": 11,  # Not used at present
    "Gross Credit (GC)": 12,  # Not used at present
    "Exchange Rate": 13,  # Not used at present
    "Net Currency": 14,
    "Net Debit (NC)": 15,  # Fee or Merchant Payout
    "Net Credit (NC)": 16,
    "Commission (NC)": 17,
    "Markup (NC)": 18,
    "Scheme Fees (NC)": 19,
    "Interchange (NC)": 20,
    "Payment Method Variant": 21,
    "Modification Merchant Reference": 22,  # Not used at present
    "Batch Number": 23,
    "Reserved4": 24,  # Not used at present
    "Reserved5": 25,  # Not used at present
    "Reserved6": 26,  # Not used at present
    "Reserved7": 27,  # Not used at present
    "Reserved8": 28,  # Not used at present
    "Reserved9": 29,  # Not used at present
    "Reserved10": 30,  # Not used at present
}


class AccountBankStatementImportAdyenParser(models.TransientModel):
    """Parse Adyen statement files for bank import."""

    _name = "account.bank.statement.import.adyen.parser"
    _description = "Account Bank Statement Import Adyen Parser"

    def parse_rows(self, rows):
        """Parse rows generated from an Adyen file.

        An Exception will be thrown if file cannot be parsed.
        """
        statement = None
        fees = 0.0
        balance = 0.0
        payout = 0.0
        num_rows = self._process_headers(rows)
        for row in rows:
            num_rows += 1
            if not self._is_transaction_row(row):
                continue
            if not statement:
                statement = self._make_statement(row)
                statement_info = self._get_statement_info(row)
            row_type = self._get_value(row, "Type").strip()
            if row_type == "MerchantPayout":
                payout -= self._balance(row)
            else:
                balance += self._balance(row)
            transaction = self._get_transaction(row)
            self._append_transaction(statement, transaction)
            fees += self._sum_fees(row)
        if fees:
            balance -= fees
            self._append_fees_transaction(
                statement, fees, statement_info["batch_number"]
            )
        self._validate_statement(statement, payout, balance)
        _logger.info(
            _("Processed %d rows from Adyen statement file with %d transactions"),
            num_rows,
            len(statement["transactions"]),
        )
        return (
            statement_info["currency_code"],
            statement_info["merchant_account"],
            [statement],
        )

    def _process_headers(self, rows):
        """Process the headers in the generated rows."""
        num_rows = 0
        for row in rows:
            num_rows += 1
            if not row[1]:
                continue
            on_header_row = self._check_header_row(row)
            if not on_header_row:
                continue
            self._set_columns(row)
            return num_rows
        raise ValueError(
            "Not an Adyen statement. Did not encounter header row in %d rows."
            % (num_rows,)
        )

    def _is_transaction_row(self, row):
        """Check wether row is a not empty and valid transaction row."""
        if not row[1]:
            return False
        if len(row) < 24:
            raise ValueError(
                "Not an Adyen statement. Unexpected row length %s "
                "less then minimum of 24" % len(row)
            )
        return True

    def _get_statement_info(self, row):
        """Get general information for statement."""
        merchant_account = self._get_value(row, "Merchant Account")
        self._validate_merchant_account(merchant_account)
        batch_number = self._get_value(row, "Batch Number")
        currency_code = self._get_value(row, "Net Currency")
        return {
            "merchant_account": merchant_account,
            "batch_number": batch_number,
            "currency_code": currency_code,
        }

    def _validate_merchant_account(self, merchant_account):
        """Check wether merchant account exist, and belongs to the correct journal."""
        journal = self.env["account.journal"].search(
            [("adyen_merchant_account", "=", merchant_account)], limit=1
        )
        if not journal:
            raise UserError(
                _("No journal refers to Merchant Account %s") % merchant_account
            )
        if self._context.get("journal_id", journal.id) != journal.id:
            raise UserError(
                _(
                    "Selected journal Merchant Account does not match "
                    "the import file Merchant Account "
                    "column: %s"
                )
                % merchant_account
            )

    def _check_header_row(self, row):
        """Header row is the first one with a "Company Account" header cell."""
        for cell in row:
            if cell == "Company Account":
                return True
        return False

    def _set_columns(self, row):
        """Set columns from headers. There MUST be a 'Company Account' header."""
        seen_company_account = False
        for num, header in enumerate(row):
            if not header.strip():
                continue  # Ignore empty columns.
            if header == "Company Account":
                seen_company_account = True
            if header not in COLUMNS:
                _logger.debug(_("Unknown header %s in Adyen statement headers"), header)
            else:
                COLUMNS[header] = num  # Set the right number for the column.
        if not seen_company_account:
            raise ValueError(
                _("Not an Adyen statement. Headers %s do not contain 'Company Account'")
                % ", ".join(row)
            )

    def _validate_statement(self, statement, payout, balance):
        """Check wether statement valid: balanced. Log when no payout."""
        if statement["transactions"] and not payout:
            _logger.info(_("No payout detected in Adyen statement."))
        if self.env.user.company_id.currency_id.compare_amounts(balance, payout) != 0:
            raise UserError(
                _("Parse error. Balance %s not equal to merchant " "payout %s")
                % (balance, payout)
            )

    def _get_value(self, row, column):
        """Get the value from the righ column in the row."""
        return row[COLUMNS[column]]

    def _make_statement(self, row):
        """Make statement on first transaction in file."""
        statement = {"transactions": []}
        statement["name"] = "{merchant} {year}/{batch}".format(
            merchant=self._get_value(row, "Merchant Account"),
            year=self._get_value(row, "Creation Date")[:4],
            batch=self._get_value(row, "Batch Number"),
        )
        statement["date"] = self._get_transaction_date(row)
        return statement

    def _get_transaction_date(self, row):
        """Get transaction date in right format."""
        return fields.Date.from_string(self._get_value(row, "Creation Date"))

    def _balance(self, row):
        return (
            -self._sum_amount_values(row, ("Net Debit (NC)",))
            + self._sum_amount_values(row, ("Net Credit (NC)",))
            + self._sum_fees(row)
        )

    def _sum_fees(self, row):
        """Sum the amounts in the fees columns."""
        return self._sum_amount_values(
            row,
            ("Commission (NC)", "Markup (NC)", "Scheme Fees (NC)", "Interchange (NC)",),
        )

    def _sum_amount_values(self, row, columns):
        """Sum the amounts from the columns passed."""
        amount = 0.0
        for column in columns:
            value = self._get_value(row, column)
            if value:
                amount += float(value)
        return amount

    def _get_transaction(self, row):
        """Get transaction from row.

        This can easily be overwritten in custom modules to add extra information.
        """
        merchant_account = self._get_value(row, "Merchant Account")
        psp_reference = self._get_value(row, "Psp Reference")
        merchant_reference = self._get_value(row, "Merchant Reference")
        payment_method = self._get_value(row, "Payment Method Variant")
        modification_reference = self._get_value(row, "Modification Reference")
        transaction = {
            "date": self._get_transaction_date(row),
            "amount": self._balance(row),
        }
        transaction["note"] = " ".join(
            [
                part
                for part in [
                    merchant_account,
                    psp_reference,
                    merchant_reference,
                    payment_method,
                ]
                if part
            ]
        )
        transaction["name"] = (
            merchant_reference or psp_reference or modification_reference
        )
        transaction["ref"] = (
            psp_reference or modification_reference or merchant_reference
        )
        transaction["transaction_type"] = self._get_value(row, "Type")
        return transaction

    def _append_fees_transaction(self, statement, fees, batch_number):
        """Single transaction for all fees in statement."""
        max_date = max(t["date"] for t in statement["transactions"])
        transaction = {
            "date": max_date,
            "amount": -fees,
            "name": "Commission, markup etc. batch %s" % batch_number,
        }
        self._append_transaction(statement, transaction)

    def _append_transaction(self, statement, transaction):
        """Add transaction with unique import id to statement."""
        # Statement date is date of earliest transaction in file.
        if transaction["date"] < statement.get("date"):
            statement["date"] = transaction["date"]
        transaction["unique_import_id"] = self._get_unique_import_id(statement)
        statement["transactions"].append(transaction)

    def _get_unique_import_id(self, statement):
        """get unique import ID for transaction."""
        return statement["name"] + str(len(statement["transactions"])).zfill(4)
