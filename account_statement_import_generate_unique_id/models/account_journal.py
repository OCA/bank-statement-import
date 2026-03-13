# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import hashlib
import json
from collections import Counter

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountJournal(models.Model):
    _inherit = "account.journal"

    generate_unique_import_id = fields.Boolean(
        string="Generate Missing Import IDs",
        help="Ensures that a unique_import_id is set on bank statement lines "
        "when importing them via bank statement import. "
        "If no unique identifier was provided, the value is a hash of the "
        "account number, date, payment reference, amount, reference and "
        "partner name. Identical transactions within the same import are "
        "numbered. Only lines imported after enabling this option get an ID; "
        "for existing lines without ID use the 'Generate for Existing Lines' "
        "button.",
    )

    @api.model
    def _get_unique_identifier_keys(self):
        return [
            "account_number",
            "date",
            "payment_ref",
            "amount",
            "ref",
            "partner_name",
        ]

    def _normalize_unique_identifier_value(self, key, value):
        """Hook for extension: normalize a value so that the same transaction
        always leads to the same hash, whatever format it was imported from"""
        if key == "amount":
            currency = self.currency_id or self.company_id.currency_id
            return currency.round(float(value or 0.0))
        if not value:
            return None
        if key == "account_number":
            return self._sanitize_bank_account_number(value)
        if key == "partner_name":
            return str(value).strip().lower()
        if isinstance(value, str):
            return value.strip()
        return value

    def _generate_statement_line_unique_import_id(self, st_line_vals):
        data = {
            key: self._normalize_unique_identifier_value(key, st_line_vals.get(key))
            for key in self._get_unique_identifier_keys()
        }
        payload = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode()).hexdigest()

    def _get_unique_import_id_occurrences(self):
        """Return the counter of the generated ids of the current import"""
        self.ensure_one()
        occurrences = self.env.cr.cache.setdefault(
            "generate_unique_import_id_occurrences", {}
        )
        return occurrences.setdefault(self.id, Counter())

    def _statement_line_import_speeddict(self):
        # The speeddict is computed once per import before processing its
        # lines, so a new import starts here: reset the occurrence counter
        speeddict = super()._statement_line_import_speeddict()
        self._get_unique_import_id_occurrences().clear()
        return speeddict

    def _statement_line_import_update_unique_import_id(
        self, st_line_vals, account_number
    ):
        self.ensure_one()
        if not st_line_vals.get("unique_import_id") and self.generate_unique_import_id:
            unique_import_id = self._generate_statement_line_unique_import_id(
                st_line_vals
            )
            # Identical transactions within the same import get a sequence
            # number so they are not considered as already imported
            occurrences = self._get_unique_import_id_occurrences()
            occurrences[unique_import_id] += 1
            if occurrences[unique_import_id] > 1:
                unique_import_id += f"-{occurrences[unique_import_id]}"
            st_line_vals["unique_import_id"] = unique_import_id
        return super()._statement_line_import_update_unique_import_id(
            st_line_vals, account_number
        )

    def _prepare_unique_import_id_vals(self, st_line):
        """Return the values of an existing statement line as they would
        be provided by an import"""
        return {key: st_line[key] for key in self._get_unique_identifier_keys()}

    def action_generate_unique_import_ids(self):
        """Generate the unique_import_id of the existing statement lines
        which have none, the same way an import of all of them would"""
        self.ensure_one()
        if not self.generate_unique_import_id:
            raise UserError(
                self.env._(
                    "Enable 'Generate Missing Import IDs' on journal %s first.",
                    self.display_name,
                )
            )
        st_lines = self.env["account.bank.statement.line"].search(
            [("journal_id", "=", self.id), ("unique_import_id", "=", False)],
            order="date, sequence, id",
        )
        used_ids = set(
            self.env["account.bank.statement.line"]
            .search([("journal_id", "=", self.id), ("unique_import_id", "!=", False)])
            .mapped("unique_import_id")
        )
        account_number = self.bank_account_id.acc_number
        self._statement_line_import_speeddict()
        skipped_st_lines = self.env["account.bank.statement.line"]
        for st_line in st_lines:
            st_line_vals = self._prepare_unique_import_id_vals(st_line)
            self._statement_line_import_update_unique_import_id(
                st_line_vals, account_number
            )
            unique_import_id = st_line_vals["unique_import_id"]
            # The id is already used by another line, which may be a
            # duplicate of this one: leave it to the user to check them
            if unique_import_id in used_ids:
                skipped_st_lines |= st_line
                continue
            used_ids.add(unique_import_id)
            st_line.unique_import_id = unique_import_id
        message = self.env._(
            "%s statement lines got an import ID.",
            len(st_lines - skipped_st_lines),
        )
        if skipped_st_lines:
            message += " " + self.env._(
                "%s statement lines were skipped because their import ID is "
                "already used by another line, they may be duplicates.",
                len(skipped_st_lines),
            )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "type": "warning" if skipped_st_lines else "success",
                "sticky": bool(skipped_st_lines),
                "message": message,
            },
        }
