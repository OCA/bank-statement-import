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


class AccountBankStatementImport(models.TransientModel):
    """Add import of Adyen statements."""

    _inherit = "account.bank.statement.import"

    def _parse_file(self, data_file):
        """Parse an Adyen xlsx file and map merchant account strings to journals."""
        try:
            _logger.debug(_("Try parsing as Adyen settlement details."))
            return self._parse_adyen_file(data_file)
        except Exception:  # pylint: disable=broad-except
            message = _("Statement file was not a Adyen settlement details file.")
            if self.env.context.get("account_bank_statement_import_adyen", False):
                raise UserError(message)
            _logger.debug(message, exc_info=True)
            return super()._parse_file(data_file)

    def _find_additional_data(self, currency_code, account_number):
        """Check if journal passed in the context matches Adyen Merchant Account."""
        if account_number:
            journal = self.env["account.journal"].search(
                [("adyen_merchant_account", "=", account_number)], limit=1
            )
            if journal:
                if self._context.get("journal_id", journal.id) != journal.id:
                    raise UserError(
                        _(
                            "Selected journal Merchant Account does not match "
                            "the import file Merchant Account "
                            "column: %s"
                        )
                        % account_number
                    )
        return super()._find_additional_data(currency_code, account_number)

    def _parse_adyen_file(self, data_file):
        """Parse file assuming it is an Adyen file.

        An Exception will be thrown if file cannot be parsed.
        """
        statement = None
        headers = False
        batch_number = False
        fees = 0.0
        balance = 0.0
        payout = 0.0
        rows = self._get_rows(data_file)
        num_rows = 0
        num_transactions = 0
        for row in rows:
            num_rows += 1
            if not row[1]:
                continue
            if not headers:
                on_header_row = self._check_header_row(row)
                if not on_header_row:
                    continue
                self._set_columns(row)
                headers = True
                continue
            if len(row) < 24:
                raise ValueError(
                    "Not an Adyen statement. Unexpected row length %s "
                    "less then minimum of 24" % len(row)
                )
            if not statement:
                batch_number = self._get_value(row, "Batch Number")
                statement = self._make_statement(row)
                currency_code = self._get_value(row, "Net Currency")
                merchant_id = self._get_value(row, "Merchant Account")
            else:
                self._update_statement(statement, row)
            row_type = self._get_value(row, "Type").strip()
            if row_type == "MerchantPayout":
                payout -= self._balance(row)
            else:
                balance += self._balance(row)
            num_transactions += 1
            self._import_adyen_transaction(statement, row)
            fees += self._sum_fees(row)
        if not headers:
            raise ValueError(
                "Not an Adyen statement. Did not encounter header row in %d rows."
                % (num_rows,)
            )
        if fees:
            balance -= fees
            self._add_fees_transaction(statement, fees, batch_number)
        if statement["transactions"] and not payout:
            raise UserError(_("No payout detected in Adyen statement."))
        if self.env.user.company_id.currency_id.compare_amounts(balance, payout) != 0:
            raise UserError(
                _("Parse error. Balance %s not equal to merchant " "payout %s")
                % (balance, payout)
            )
        _logger.info(
            _("Processed %d rows from Adyen statement file with %d transactions"),
            num_rows,
            num_transactions,
        )
        return currency_code, merchant_id, [statement]

    def _get_rows(self, data_file):
        """Get rows from data_file."""
        # Try to use original import file name.
        filename = (
            self.attachment_ids[0].name
            if len(self.attachment_ids) == 1
            else "Ayden settlement details"
        )
        import_model = self.env["base_import.import"]
        importer = import_model.create({"file": data_file, "file_name": filename})
        return importer._read_file({"quoting": '"', "separator": ","})

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

    def _update_statement(self, statement, row):
        """Update statement from transaction row."""
        # Statement date is date of earliest transaction in file.
        date = self._get_transaction_date(row)
        if date < statement.get("date"):
            statement["date"] = date

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

    def _import_adyen_transaction(self, statement, row):
        """Add transaction from row to statements."""
        transaction = dict(
            unique_import_id=self._get_unique_import_id(statement),
            date=self._get_transaction_date(row),
            amount=self._balance(row),
            note="{} {} {} {}".format(
                self._get_value(row, "Merchant Account"),
                self._get_value(row, "Psp Reference"),
                self._get_value(row, "Merchant Reference"),
                self._get_value(row, "Payment Method Variant"),
            ),
            name="%s"
            % (
                self._get_value(row, "Psp Reference")
                or self._get_value(row, "Merchant Reference")
                or self._get_value(row, "Modification Reference")
            ),
        )
        statement["transactions"].append(transaction)

    def _get_unique_import_id(self, statement):
        """get unique import ID for transaction."""
        return statement["name"] + str(len(statement["transactions"])).zfill(4)

    def _add_fees_transaction(self, statement, fees, batch_number):
        """Single transaction for all fees in statement."""
        transaction = dict(
            unique_import_id=self._get_unique_import_id(statement),
            date=max(t["date"] for t in statement["transactions"]),
            amount=-fees,
            name="Commission, markup etc. batch %s" % batch_number,
        )
        statement["transactions"].append(transaction)
