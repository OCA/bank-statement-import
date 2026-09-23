# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0.html
import odoo.tests.common as common


class TestGenerateUniqueImportId(common.TransactionCase):
    def test_unique_import_id(self):
        journal = self.env["account.journal"].create(
            {
                "name": "Test Journal",
                "code": "AST-1",
                "type": "bank",
            }
        )
        st_line_vals = {
            "account_number": "1234",
            "date": "2026-03-13",
            "payment_ref": "Payment",
            "amount": 100.0,
        }
        account_number = "11111"
        unique_import_id_prefix = f"{account_number}-{journal.id}"
        journal._statement_line_import_update_unique_import_id(
            st_line_vals, account_number
        )
        self.assertFalse(st_line_vals.get("unique_imort_id"))
        st_line_vals["unique_import_id"] = "unique_import_id"
        journal._statement_line_import_update_unique_import_id(
            st_line_vals, account_number
        )
        self.assertEqual(
            st_line_vals.get("unique_import_id"),
            f"{unique_import_id_prefix}-unique_import_id",
        )
        st_line_vals.pop("unique_import_id")
        journal.ensure_unique_import_id = True
        journal._statement_line_import_update_unique_import_id(
            st_line_vals, account_number
        )
        self.assertEqual(
            st_line_vals.get("unique_import_id"),
            f"{unique_import_id_prefix}-1234-2026-03-13-Payment-100.0",
        )
        st_line_vals.pop("date")
        st_line_vals.pop("unique_import_id")
        journal._statement_line_import_update_unique_import_id(
            st_line_vals, account_number
        )
        self.assertEqual(
            st_line_vals.get("unique_import_id"),
            f"{unique_import_id_prefix}-1234-Payment-100.0",
        )
        st_line_vals["unique_import_id"] = "unique_import_id"
        journal._statement_line_import_update_unique_import_id(
            st_line_vals, account_number
        )
        self.assertEqual(
            st_line_vals.get("unique_import_id"),
            f"{unique_import_id_prefix}-unique_import_id",
        )
