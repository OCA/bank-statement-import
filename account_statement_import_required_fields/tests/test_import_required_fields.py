# Copyright 2026 Heliconia Solutions Pvt. Ltd.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from csv import reader
from io import StringIO

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import common


class TestImportRequiredFields(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.mapping = cls.env["account.statement.import.sheet.mapping"].create(
            {
                "name": "Test Mapping",
                "timestamp_format": "%Y-%m-%d",
                "timestamp_column": "Date",
                "description_column": "Description",
                "amount_type": "simple_value",
                "amount_column": "Amount",
                "header_lines_skip_count": 1,
            }
        )
        # Set required fields
        date_field = cls.env["ir.model.fields"].search(
            [
                ("model", "=", "account.statement.import.sheet.mapping"),
                ("name", "=", "timestamp_column"),
            ],
            limit=1,
        )
        cls.mapping.required_field_ids = [Command.set([date_field.id])]
        cls.parser = cls.env["account.statement.import.sheet.parser"].create({})

    def _get_columns(self, extra=None):
        cols = {
            "timestamp_column": [],
            "currency_column": [],
            "amount_column": [],
            "amount_debit_column": [],
            "amount_credit_column": [],
            "balance_column": [],
            "original_currency_column": [],
            "original_amount_column": [],
            "debit_credit_column": [],
            "transaction_id_column": [],
            "description_column": [],
            "notes_column": [],
            "reference_column": [],
            "partner_name_column": [],
            "bank_name_column": [],
            "bank_account_column": [],
        }
        if extra:
            cols.update(extra)
        return cols

    def test_import_missing_required_field(self):
        """Test import with a missing required field (Description)"""
        raw_data = b"Date,Description,Amount\n2026-03-25,,100.0"
        csv_reader = reader(StringIO(raw_data.decode()))
        next(csv_reader)  # Skip header
        columns = self._get_columns(
            {"timestamp_column": [0], "description_column": [1], "amount_column": [2]}
        )
        desc_field = self.env["ir.model.fields"].search(
            [
                ("model", "=", "account.statement.import.sheet.mapping"),
                ("name", "=", "description_column"),
            ],
            limit=1,
        )
        self.mapping.required_field_ids = [Command.set([desc_field.id])]
        with self.assertRaises(ValidationError) as e:
            self.parser._parse_rows(
                self.mapping, "EUR", (csv_reader, raw_data), columns
            )

        self.assertIn(
            "The following required columns are missing data", e.exception.args[0]
        )
        self.assertIn("• Description", e.exception.args[0])

    def test_import_with_required_field(self):
        """Test import with all required fields present"""
        raw_data = b"Date,Description,Amount\n2026-03-25,Test line,100.0"
        csv_reader = reader(StringIO(raw_data.decode()))
        next(csv_reader)  # Skip header
        columns = self._get_columns(
            {"timestamp_column": [0], "description_column": [1], "amount_column": [2]}
        )
        rows = self.parser._parse_rows(
            self.mapping, "EUR", (csv_reader, raw_data), columns
        )
        self.assertEqual(len(rows), 1)

    def test_debit_credit_smart_handling(self):
        """Test smart handling for Debit and Credit columns"""
        self.mapping.write(
            {
                "amount_type": "distinct_credit_debit",
                "amount_debit_column": "Debit",
                "amount_credit_column": "Credit",
            }
        )
        debit_field = self.env["ir.model.fields"].search(
            [
                ("model", "=", "account.statement.import.sheet.mapping"),
                ("name", "=", "amount_debit_column"),
            ],
            limit=1,
        )
        credit_field = self.env["ir.model.fields"].search(
            [
                ("model", "=", "account.statement.import.sheet.mapping"),
                ("name", "=", "amount_credit_column"),
            ],
            limit=1,
        )
        self.mapping.required_field_ids = [
            Command.set([debit_field.id, credit_field.id])
        ]
        columns = self._get_columns(
            {
                "timestamp_column": [0],
                "amount_debit_column": [1],
                "amount_credit_column": [2],
            }
        )

        # Case 1: Both missing -> Should fail
        raw_missing = b"Date,Debit,Credit\n2026-03-25,,"
        csv_missing = reader(StringIO(raw_missing.decode()))
        next(csv_missing)  # Skip header
        with self.assertRaises(ValidationError):
            self.parser._parse_rows(
                self.mapping, "EUR", (csv_missing, raw_missing), columns
            )

        # Case 2: Only Debit present -> Should pass
        raw_debit = b"Date,Debit,Credit\n2026-03-25,100.0,"
        csv_debit = reader(StringIO(raw_debit.decode()))
        next(csv_debit)  # Skip header
        rows = self.parser._parse_rows(
            self.mapping, "EUR", (csv_debit, raw_debit), columns
        )
        self.assertEqual(len(rows), 1)

        # Case 3: Only Credit present -> Should pass
        raw_credit = b"Date,Debit,Credit\n2026-03-25,,100.0"
        csv_credit = reader(StringIO(raw_credit.decode()))
        next(csv_credit)  # Skip header
        rows = self.parser._parse_rows(
            self.mapping, "EUR", (csv_credit, raw_credit), columns
        )
        self.assertEqual(len(rows), 1)
