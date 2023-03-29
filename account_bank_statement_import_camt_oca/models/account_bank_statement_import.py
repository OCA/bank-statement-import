# Copyright 2013-2021 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
import logging
import zipfile
from io import BytesIO

from odoo import _, models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    def _parse_file(self, data_file):
        """Parse a CAMT053 XML file."""
        try:
            parser = self.env["account.bank.statement.import.camt.parser"]
            _logger.debug("Try parsing with camt.")
            return parser.parse(data_file)
        except ValueError:
            try:
                with zipfile.ZipFile(BytesIO(data_file)) as data:
                    currency = None
                    account_number = None
                    transactions = []
                    for member in data.namelist():
                        currency, account_number, new = parser.parse(
                            data.open(member).read()
                        )
                        transactions.extend(new)
                return currency, account_number, transactions
            except (zipfile.BadZipFile, ValueError):
                pass
            # Not a camt file, returning super will call next candidate:
            _logger.debug("Statement file was not a camt file.", exc_info=True)
        return super(AccountBankStatementImport, self)._parse_file(data_file)

    def _complete_stmts_vals(self, stmts_vals, journal, account_number):
        stmts_vals = super()._complete_stmts_vals(stmts_vals, journal, account_number)
        for st_vals in stmts_vals:
            camt054_updated_statement_line_ids = []
            for line_vals in st_vals["transactions"]:
                unique_import_id = line_vals.get("unique_import_id")
                sl = self.env["account.bank.statement.line"].search(
                    [("unique_import_id", "=", unique_import_id)], limit=1
                )
                if sl and not sl.journal_entry_ids:
                    if not sl.partner_name and "partner_name" in line_vals:
                        sl.partner_name = line_vals["partner_name"]
                        camt054_updated_statement_line_ids.append(sl.id)
                    if sl.name == "/" and "partner_name" in line_vals:
                        sl.name = line_vals["name"]
                        camt054_updated_statement_line_ids.append(sl.id)
            st_vals["camt054_updated_statement_line_ids"] = list(
                set(camt054_updated_statement_line_ids)
            )
        return stmts_vals

    def _create_bank_statements(self, stmts_vals):
        BankStatementLine = self.env["account.bank.statement.line"]
        new_stmts_vals = []
        notifications = []
        for stmt_vals in stmts_vals:
            stmt_vals.get("camt054_transactions_updated", False)
            is_camt054 = stmt_vals.get("is_camt054", False)
            if "is_camt054" in stmt_vals:
                stmt_vals.pop("is_camt054")
            camt054_updated_statement_line_ids = stmt_vals.get(
                "camt054_updated_statement_line_ids", []
            )
            if "camt054_updated_statement_line_ids" in stmt_vals:
                stmt_vals.pop("camt054_updated_statement_line_ids")
            if camt054_updated_statement_line_ids:
                notifications.append(
                    {
                        "type": "info",
                        "message": _(
                            "%s transactions have been updated with additional details."
                        )
                        % len(camt054_updated_statement_line_ids),
                        "details": {
                            "name": _("Already imported items"),
                            "model": "account.bank.statement.line",
                            "ids": BankStatementLine.search(
                                [
                                    (
                                        "unique_import_id",
                                        "in",
                                        camt054_updated_statement_line_ids,
                                    )
                                ]
                            ).ids,
                        },
                    }
                )
            if not is_camt054:
                new_stmts_vals.append(stmt_vals)
        if new_stmts_vals:
            return super()._create_bank_statements(new_stmts_vals)
        else:
            return [], notifications
