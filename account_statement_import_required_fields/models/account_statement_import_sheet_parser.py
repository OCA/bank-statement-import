# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.exceptions import ValidationError


class AccountStatementImportSheetParser(models.TransientModel):
    _inherit = "account.statement.import.sheet.parser"

    def _parse_rows(self, mapping, currency_code, data, columns):
        missing_cols = set()
        parser = self
        if mapping.required_field_ids:
            required_field_names = mapping.required_field_ids.mapped("name")
            parser = self.with_context(
                mapping_required_fields=required_field_names,
                missing_required_columns=missing_cols,
            )

        rows = super(AccountStatementImportSheetParser, parser)._parse_rows(
            mapping, currency_code, data, columns
        )

        if not rows:
            return rows

        if missing_cols:
            missing_field_labels = [
                f"• {getattr(mapping, col)}" for col in missing_cols
            ]
            raise ValidationError(
                self.env._(
                    "The bank statement could not be imported. "
                    "The following required columns are missing data in one or "
                    "more rows:\n\n"
                    "%(missing_field_names)s\n\n"
                    "Please verify your file and ensure these columns have values "
                    "where expected.",
                    missing_field_names="\n".join(missing_field_labels),
                )
            )
        return rows

    def _get_values_from_column(self, values, columns, column_name):
        res = super()._get_values_from_column(values, columns, column_name)

        required_fields = self.env.context.get("mapping_required_fields", [])
        if required_fields and column_name == "timestamp_column":
            # 'timestamp_column' is an anchor, evaluated once per row.
            row_missing = []
            for req_col in required_fields:
                if not columns.get(req_col):
                    continue
                val = super()._get_values_from_column(values, columns, req_col)
                if val is None or (isinstance(val, str) and str(val).strip() == ""):
                    row_missing.append(req_col)

            # Special case for debit and credit amount columns
            if (
                "amount_debit_column" in required_fields
                and "amount_credit_column" in required_fields
            ):
                has_debit = "amount_debit_column" not in row_missing
                has_credit = "amount_credit_column" not in row_missing
                if has_debit or has_credit:
                    # At least one has a value, so remove both from the missing list
                    if "amount_debit_column" in row_missing:
                        row_missing.remove("amount_debit_column")
                    if "amount_credit_column" in row_missing:
                        row_missing.remove("amount_credit_column")

            if row_missing:
                missing_set = self.env.context.get("missing_required_columns")
                if missing_set is not None:
                    for col in row_missing:
                        missing_set.add(col)

        return res
