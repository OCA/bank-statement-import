# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models


class AccountStatementImportRequiredField(models.Model):
    _inherit = "account.statement.import.sheet.mapping"

    available_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        compute="_compute_available_field_ids",
    )

    required_field_ids = fields.Many2many(
        comodel_name="ir.model.fields",
        relation="account_stmt_mapping_req_fld_rel",
        column1="mapping_id",
        column2="field_id",
        string="Mandatory Mapping Columns",
        help="Select which mapped columns must have a value in every row of "
        "the imported file. "
        "\nSpecial case: If you select both Debit and Credit columns, "
        "at least one of them must be present in a given row.",
        domain="[('id', 'in', available_field_ids)]",
    )

    @api.depends(
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
    )
    def _compute_available_field_ids(self):
        column_fields = [
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
        for record in self:
            valid_field_names = []
            for field_name in column_fields:
                if getattr(record, field_name):
                    valid_field_names.append(field_name)

            if valid_field_names:
                fields_records = (
                    self.env["ir.model.fields"]
                    .sudo()
                    .search(
                        [
                            ("model", "=", "account.statement.import.sheet.mapping"),
                            ("name", "in", valid_field_names),
                        ]
                    )
                )
                record.available_field_ids = fields_records
            else:
                record.available_field_ids = False

    @api.onchange("available_field_ids")
    def _onchange_available_field_ids(self):
        for record in self:
            if record.required_field_ids:
                record.required_field_ids = (
                    record.required_field_ids & record.available_field_ids
                )
