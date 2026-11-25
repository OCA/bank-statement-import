# Copyright 2026 Akretion (https://www.akretion.com).
# @author Renato Lima <renato.lima@akretion.com.br>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

from odoo.tests.common import TransactionCase

from odoo.addons.account_statement_import_partner_by_vat.tools import (
    extract_vat_candidates,
    is_valid_cnpj,
    is_valid_cpf,
)

CNPJ = "11.222.333/0001-81"
CNPJ_DIGITS = "11222333000181"
CPF = "111.444.777-35"
CPF_DIGITS = "11144477735"
OTHER_CNPJ = "45.723.174/0001-10"


class TestPartnerByVat(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.ref("base.main_company")
        cls.br = cls.env.ref("base.br")
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "Bank Journal TEST VAT",
                "code": "BNKVA",
                "type": "bank",
                "company_id": cls.company.id,
            }
        )
        cls.partner = cls._create_partner("Acme LTDA", CNPJ)
        cls.speeddict = cls.journal._statement_line_import_speeddict()

    @classmethod
    def _create_partner(cls, name, vat, **kwargs):
        return cls.env["res.partner"].create(
            dict({"name": name, "vat": vat, "country_id": cls.br.id}, **kwargs)
        )

    def _match(self, payment_ref, speeddict=None):
        """Run the import hook on a line and return the partner it matched."""
        st_line_vals = {"payment_ref": payment_ref, "amount": 100.0}
        self.journal._statement_line_import_update_hook(
            st_line_vals, speeddict or self.speeddict
        )
        return st_line_vals.get("partner_id")

    # Check digits

    def test_valid_cnpj(self):
        self.assertTrue(is_valid_cnpj(CNPJ_DIGITS))

    def test_invalid_cnpj_check_digits(self):
        self.assertFalse(is_valid_cnpj("11222333000182"))

    def test_invalid_cnpj_repeated_digits(self):
        self.assertFalse(is_valid_cnpj("11111111111111"))

    def test_valid_cpf(self):
        self.assertTrue(is_valid_cpf(CPF_DIGITS))

    def test_invalid_cpf_check_digits(self):
        self.assertFalse(is_valid_cpf("11144477736"))

    def test_invalid_cpf_repeated_digits(self):
        self.assertFalse(is_valid_cpf("00000000000"))

    # Extraction from a label

    def test_extract_masked(self):
        self.assertEqual(
            list(extract_vat_candidates(f"PIX RECEBIDO {CNPJ} ACME")),
            [CNPJ_DIGITS],
        )

    def test_extract_unmasked(self):
        self.assertEqual(
            list(extract_vat_candidates(f"TED {CNPJ_DIGITS} ACME")),
            [CNPJ_DIGITS],
        )

    def test_extract_cpf(self):
        self.assertEqual(list(extract_vat_candidates(f"PIX {CPF}")), [CPF_DIGITS])

    def test_extract_ignores_dates_and_amounts(self):
        self.assertEqual(
            list(extract_vat_candidates("TARIFA 05/01/2026 REF 1234-5678 R$ 12,50")),
            [],
        )

    def test_extract_ignores_wrong_check_digits(self):
        self.assertEqual(
            list(extract_vat_candidates("DOC 11.222.333/0001-82")),
            [],
        )

    def test_extract_reports_each_number_once(self):
        label = f"PIX {CNPJ} DEV {CNPJ}"
        self.assertEqual(list(extract_vat_candidates(label)), [CNPJ_DIGITS])

    # Matching against the speeddict

    def test_match_masked(self):
        self.assertEqual(self._match(f"PIX RECEBIDO {CNPJ} ACME"), self.partner.id)

    def test_match_unmasked(self):
        self.assertEqual(self._match(f"TED {CNPJ_DIGITS} ACME"), self.partner.id)

    def test_no_match_on_unknown_vat(self):
        self.assertFalse(self._match(f"PIX {OTHER_CNPJ}"))

    def test_no_match_on_label_without_vat(self):
        self.assertFalse(self._match("TARIFA MENSALIDADE"))

    def test_existing_partner_is_kept(self):
        other = self._create_partner("Other LTDA", OTHER_CNPJ)
        speeddict = self.journal._statement_line_import_speeddict()
        st_line_vals = {
            "payment_ref": f"PIX {CNPJ}",
            "partner_id": other.id,
            "amount": 100.0,
        }
        self.journal._statement_line_import_update_hook(st_line_vals, speeddict)
        self.assertEqual(st_line_vals["partner_id"], other.id)

    def test_own_company_vat_is_not_matched(self):
        """A label repeating the VAT of the company must not match it."""
        self.company.partner_id.write({"country_id": self.br.id, "vat": OTHER_CNPJ})
        speeddict = self.journal._statement_line_import_speeddict()
        self.assertFalse(self._match(f"TARIFA {OTHER_CNPJ}", speeddict))

    def test_child_contact_resolves_to_commercial_partner(self):
        """A VAT shared by a company and its contact matches the company."""
        parent = self._create_partner("Parent LTDA", OTHER_CNPJ, is_company=True)
        self._create_partner("Child", OTHER_CNPJ, parent_id=parent.id)
        speeddict = self.journal._statement_line_import_speeddict()
        self.assertEqual(self._match(f"PIX {OTHER_CNPJ}", speeddict), parent.id)
