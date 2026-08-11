# Copyright 2020 Camptocamp SA
# Copyright 2020 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64

from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path


class TestGenerateBankStatement(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        eur_currency = cls.env.ref("base.EUR")
        eur_currency.write({"active": True})
        bank = cls.env["res.partner.bank"].create(
            {
                # test-camt054's Ntry/NtryRef, not its Acct/IBAN: for camt.054
                # files the parser now matches the journal on NtryRef.
                "acc_number": "NL0000000000000000000",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL46ABNA0499998748",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank Journal - (test camt)",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": eur_currency.id,
            }
        )

    def _load_statement(self):
        testfile = file_path("account_statement_import_camt/tests/samples/test-camt054")
        with open(testfile, "rb") as datafile:
            camt_file = base64.b64encode(datafile.read())
            self.env["account.statement.import"].create(
                {
                    "statement_filename": "test import",
                    "statement_file": camt_file,
                }
            ).import_file_button()
            bank_st_record = self.env["account.bank.statement"].search(
                [
                    (
                        "name",
                        "in",
                        ["TBNKC Statement 2022-01-26", "20220120000000000000000"],
                    )
                ],
                limit=1,
            )
            statement_lines = bank_st_record.line_ids
            return statement_lines

    def test_statement_import(self):
        self.journal.transfer_line = True
        lines = self._load_statement()
        self.assertEqual(len(lines), 2)
        self.assertAlmostEqual(sum(lines.mapped("amount")), 0)
        self.journal.transfer_line = False
        lines = self._load_statement()
        self.assertEqual(len(lines), 1)
        self.assertAlmostEqual(sum(lines.mapped("amount")), 5.0)

    def test_statement_import_camt054_matches_journal_on_ntryref(self):
        """A camt.054 QR-bill notification must pick the journal whose
        account matches Ntry/NtryRef (the QR-IBAN), not the notification's
        own Acct/IBAN (the regular account both journals share)."""
        chf_currency = self.env.ref("base.CHF")
        chf_currency.write({"active": True})
        physical_account_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "CH0000000000000000001",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        self.env["account.journal"].create(
            {
                "name": "Test physical account journal (camt054)",
                "code": "TPH54",
                "type": "bank",
                "bank_account_id": physical_account_bank.id,
                "currency_id": chf_currency.id,
            }
        )
        qrr_account_bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "CH0000000000000000002",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        qrr_journal = self.env["account.journal"].create(
            {
                "name": "Test QRR journal (camt054)",
                "code": "TQR54",
                "type": "bank",
                "bank_account_id": qrr_account_bank.id,
                "currency_id": chf_currency.id,
            }
        )

        testfile = file_path(
            "account_statement_import_camt54/tests/samples/test-camt054-qrr.xml"
        )
        with open(testfile, "rb") as datafile:
            camt_file = base64.b64encode(datafile.read())
            action = (
                self.env["account.statement.import"]
                .create(
                    {
                        "statement_filename": "test-camt054-qrr.xml",
                        "statement_file": camt_file,
                    }
                )
                .import_file_button()
            )

        statement = self.env["account.bank.statement"].browse(action["domain"][0][2])
        self.assertEqual(
            statement.journal_id,
            qrr_journal,
            "Statement should have been imported into the QRR journal, "
            f"got {statement.journal_id.display_name!r}",
        )
        self.assertAlmostEqual(sum(statement.line_ids.mapped("amount")), 184.0)
