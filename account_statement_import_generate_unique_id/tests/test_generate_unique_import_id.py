# Copyright 2026 Michael Tietz (MT Software) <mtietz@mt-software.de>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).
import odoo.tests.common as common
from odoo.exceptions import UserError


class TestGenerateUniqueImportId(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Test Journal",
                "code": "AST-1",
                "type": "bank",
            }
        )
        cls.account_number = "11111"
        cls.prefix = f"{cls.account_number}-{cls.journal.id}"
        cls.st_line_vals = {
            "account_number": "1234",
            "date": "2026-03-13",
            "payment_ref": "Payment",
            "amount": 100.0,
        }

    def _import(self, *lines_vals):
        """Simulate an import of the given lines and return their ids"""
        self.journal._statement_line_import_speeddict()
        unique_import_ids = []
        for line_vals in lines_vals:
            line_vals = dict(line_vals)
            self.journal._statement_line_import_update_unique_import_id(
                line_vals, self.account_number
            )
            unique_import_ids.append(line_vals.get("unique_import_id"))
        return unique_import_ids

    def _import_one(self, **changes):
        return self._import(dict(self.st_line_vals, **changes))[0]

    def test_disabled(self):
        self.assertFalse(self._import_one())
        self.assertEqual(
            self._import_one(unique_import_id="unique_import_id"),
            f"{self.prefix}-unique_import_id",
        )

    def test_unique_import_id(self):
        self.journal.generate_unique_import_id = True
        generated_id = self._import_one()
        self.assertRegex(generated_id, rf"^{self.prefix}-[0-9a-f]{{64}}$")
        # A provided id always takes priority
        self.assertEqual(
            self._import_one(unique_import_id="unique_import_id"),
            f"{self.prefix}-unique_import_id",
        )
        # Same transaction in a differently formatted
        # account number, amount or partner name
        self.assertEqual(self._import_one(account_number="12 34"), generated_id)
        self.assertEqual(self._import_one(amount="100.00"), generated_id)
        self.assertEqual(
            self._import_one(partner_name="ACME Corp"),
            self._import_one(partner_name=" acme corp "),
        )
        # A different or missing value must lead to a different id
        self.assertNotEqual(self._import_one(ref="REF-1"), generated_id)
        self.assertNotEqual(self._import_one(date=False), generated_id)
        self.assertNotEqual(self._import_one(partner_name="ACME Corp"), generated_id)

    def test_occurrence_numbering(self):
        self.journal.generate_unique_import_id = True
        generated_id = self._import_one()
        # Identical transactions within the same import are numbered
        self.assertEqual(
            self._import(self.st_line_vals, self.st_line_vals, self.st_line_vals),
            [generated_id, f"{generated_id}-2", f"{generated_id}-3"],
        )
        # A new import starts counting again
        self.assertEqual(
            self._import(self.st_line_vals, self.st_line_vals),
            [generated_id, f"{generated_id}-2"],
        )
        # Provided ids are not numbered
        provided_vals = dict(self.st_line_vals, unique_import_id="unique_import_id")
        self.assertEqual(
            self._import(provided_vals, provided_vals),
            [f"{self.prefix}-unique_import_id"] * 2,
        )

    def _create_st_line(self, **vals):
        return self.env["account.bank.statement.line"].create(
            dict(
                {
                    "journal_id": self.journal.id,
                    "account_number": "1234",
                    "date": "2026-03-13",
                    "payment_ref": "Payment",
                    "amount": 100.0,
                },
                **vals,
            )
        )

    def test_action_generate_unique_import_ids(self):
        line_1 = self._create_st_line()
        line_2 = self._create_st_line()
        line_other = self._create_st_line(amount=50.0)
        line_provided = self._create_st_line(unique_import_id="provided")
        with self.assertRaises(UserError):
            self.journal.action_generate_unique_import_ids()
        self.journal.generate_unique_import_id = True
        # The journal has no bank account, so the ids have no account prefix
        self.account_number = False
        generated_id, other_id = self._import(
            self.st_line_vals, dict(self.st_line_vals, amount=50.0)
        )
        # An already imported line uses the id of the first identical line
        line_imported = self._create_st_line(unique_import_id=generated_id)
        action = self.journal.action_generate_unique_import_ids()
        # The id of the first line is already used, it may be a duplicate
        self.assertFalse(line_1.unique_import_id)
        self.assertEqual(line_2.unique_import_id, f"{generated_id}-2")
        self.assertEqual(action["params"]["type"], "warning")
        self.assertIn("1 statement lines were skipped", action["params"]["message"])
        self.assertEqual(line_other.unique_import_id, other_id)
        self.assertEqual(line_provided.unique_import_id, "provided")
        self.assertEqual(line_imported.unique_import_id, generated_id)
