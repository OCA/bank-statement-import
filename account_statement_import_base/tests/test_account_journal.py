# Copyright 2026 Ryan Duguid <ryan@duguid.com.au>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase


class TestAccountJournalImport(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.partner = cls.env["res.partner"].create({"name": "IBAN Vendor"})
        cls.partner_bank = cls.env["res.partner.bank"].create(
            {
                "partner_id": cls.partner.id,
                "acc_number": "DE07 3105 0000 0000 1431 56",
                "company_id": cls.env.company.id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "IBAN Bank",
                "code": "IBAN",
                "type": "bank",
            }
        )

    def test_speeddict_keys_are_sanitized(self):
        speeddict = self.journal._statement_line_import_speeddict()
        self.assertNotIn(
            "DE07 3105 0000 0000 1431 56",
            speeddict["account_number"],
        )
        self.assertEqual(
            speeddict["account_number"]["DE07310500000000143156"],
            {
                "partner_id": self.partner.id,
                "partner_bank_id": self.partner_bank.id,
            },
        )

    def test_partner_match_iban_with_spaces(self):
        """Lookup after sanitizing the imported IBAN must find the partner.

        CAMT files store IBANs without spaces. res.partner.bank often
        stores the same number with grouping spaces. The speeddict used
        to key on the raw acc_number, so the sanitized lookup missed.
        """
        speeddict = self.journal._statement_line_import_speeddict()
        vals = {"account_number": "DE07310500000000143156"}
        self.journal._statement_line_import_update_hook(vals, speeddict)
        self.assertEqual(vals["partner_id"], self.partner.id)
        self.assertEqual(vals["partner_bank_id"], self.partner_bank.id)

    def test_partner_match_iban_from_spaced_import(self):
        speeddict = self.journal._statement_line_import_speeddict()
        vals = {"account_number": "DE07 3105 0000 0000 1431 56"}
        self.journal._statement_line_import_update_hook(vals, speeddict)
        self.assertEqual(vals["account_number"], "DE07310500000000143156")
        self.assertEqual(vals["partner_id"], self.partner.id)
        self.assertEqual(vals["partner_bank_id"], self.partner_bank.id)
