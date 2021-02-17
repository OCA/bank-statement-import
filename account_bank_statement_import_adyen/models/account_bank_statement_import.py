# Copyright 2017 Opener BV (<https://opener.amsterdam>)
# Copyright 2021 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    @api.model
    def _parse_file(self, data_file):
        """Parse an Adyen xlsx file and map merchant account strings to journals."""
        try:
            return self.import_adyen_xlsx(data_file)
        except ValueError:
            return super()._parse_file(data_file)

    def _find_additional_data(self, currency_code, account_number):
        """Try to find journal by Adyen merchant account."""
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
                self = self.with_context(journal_id=journal.id)
        return super()._find_additional_data(currency_code, account_number)

    @api.model
    def balance(self, row):
        return -(float(row[15]) if row[15] else 0.0) + sum(
            float(row[i]) if row[i] else 0.0 for i in (16, 17, 18, 19, 20)
        )

    @api.model
    def import_adyen_transaction(self, statement, statement_id, row):
        transaction_id = str(len(statement["transactions"])).zfill(4)
        transaction = dict(
            unique_import_id=statement_id + transaction_id,
            date=fields.Date.from_string(row[6]),
            amount=self.balance(row),
            note="{} {} {} {}".format(row[2], row[3], row[4], row[21]),
            name="%s" % (row[3] or row[4] or row[9]),
        )
        statement["transactions"].append(transaction)

    @api.model
    def parse_adyen_file(self, data_file):
        statements = []
        statement = None
        headers = False
        fees = 0.0
        balance = 0.0
        payout = 0.0
        statement_id = None

        import_model = self.env["base_import.import"]
        importer = import_model.create(
            {"file": data_file, "file_name": "Ayden settlemnt details"}
        )
        rows = importer._read_file({})

        for row in rows:
            if len(row) != 31:
                raise ValueError(
                    "Not an Adyen statement. Unexpected row length %s "
                    "instead of 31" % len(row)
                )
            if not row[1]:
                continue
            if not headers:
                if row[1] != "Company Account":
                    raise ValueError(
                        'Not an Adyen statement. Unexpected header "%s" '
                        'instead of "Company Account"',
                        row[1],
                    )
                headers = True
                continue
            if not statement:
                statement = {"transactions": []}
                statements.append(statement)
                statement_id = "{merchant} {year}/{batch}".format(
                    merchant=row[2], year=row[6][:4], batch=row[23],
                )
                currency_code = row[14]
                merchant_id = row[2]
                statement["name"] = statement_id
            date = fields.Date.from_string(row[6])
            if not statement.get("date") or statement.get("date") > date:
                statement["date"] = date

            row[8] = row[8].strip()
            if row[8] == "MerchantPayout":
                payout -= self.balance(row)
            else:
                balance += self.balance(row)
            self.import_adyen_transaction(statement, statement_id, row)
            fees += sum(float(row[i]) if row[i] else 0.0 for i in (17, 18, 19, 20))

        if not headers:
            raise ValueError("Not an Adyen statement. Did not encounter header row.")

        if fees:
            transaction_id = str(len(statement["transactions"])).zfill(4)
            transaction = dict(
                unique_import_id=statement_id + transaction_id,
                date=max(t["date"] for t in statement["transactions"]),
                amount=-fees,
                name="Commission, markup etc. batch %s" % (int(row[23])),
            )
            balance -= fees
            statement["transactions"].append(transaction)

        if statement["transactions"] and not payout:
            raise UserError(_("No payout detected in Adyen statement."))
        if self.env.user.company_id.currency_id.compare_amounts(balance, payout) != 0:
            raise UserError(
                _("Parse error. Balance %s not equal to merchant " "payout %s")
                % (balance, payout)
            )
        return currency_code, merchant_id, statements
