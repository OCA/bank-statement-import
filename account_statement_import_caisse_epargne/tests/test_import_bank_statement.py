import base64

from odoo.tests.common import TransactionCase
from odoo.tools.misc import file_path


class TestParserCommon(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.eur_currency.write({"active": True})
        cls.bank_account = cls.env["res.partner.bank"].create(
            {"acc_number": "01234567890", "partner_id": cls.env.company.partner_id.id}
        )
        cls.import_wizard_A = cls._create_import_wizard(
            cls,
            file_path(
                "account_statement_import_caisse_epargne/tests/samples/test_statement_import_version_A.csv"
            ),
        )
        cls.import_wizard_B = cls._create_import_wizard(
            cls,
            file_path(
                "account_statement_import_caisse_epargne/tests/samples/test_statement_import_version_B.csv"
            ),
        )
        cls.import_wizard_C = cls._create_import_wizard(
            cls,
            file_path(
                "account_statement_import_caisse_epargne/tests/samples/test_statement_import_version_C.csv"
            ),
        )

    def _create_import_wizard(self, file_path):
        file = base64.b64encode(open(file_path, "rb").read())
        return self.env["account.statement.import"].create(
            {"statement_file": file, "statement_filename": "Test"}
        )

    def test_check_file(self):
        """Ensure _check_file detects version and parses header correctly."""
        for import_wizard in [
            self.import_wizard_A,
            self.import_wizard_B,
            self.import_wizard_C,
        ]:
            data_file = (
                base64.b64decode(import_wizard.statement_file)
                .decode("utf-8")
                .splitlines()
            )
            result = import_wizard._check_file(data_file)
            self.assertTrue(result, "File could not be parsed by _check_file")
            (
                version,
                bank_group_code,
                opening_date,
                closing_date,
                bank_account_number,
                opening_balance,
                closing_balance,
                currency,
            ) = result
            self.assertIn(version, ["version_A", "version_B", "version_C"])
            self.assertEqual(bank_group_code, "10101")
            self.assertEqual(bank_account_number, "01234567890")
            self.assertEqual(currency, "EUR")

    def test_parse_file(self):
        for import_wizard in [
            self.import_wizard_A,
            self.import_wizard_B,
            self.import_wizard_C,
        ]:
            data_file = base64.b64decode(import_wizard.statement_file)
            currency, bank_account_number, statements = import_wizard._parse_file(
                data_file
            )
            self.assertEqual(currency, "EUR")
            self.assertEqual(bank_account_number, "01234567890")
            self.assertEqual(len(statements), 1)
            statement = statements[0]
            self.assertIn("transactions", statement)
            self.assertGreater(len(statement["transactions"]), 0)
            # check balances align
            self.assertAlmostEqual(
                statement["balance_start"]
                + sum(t["amount"] for t in statement["transactions"]),
                statement["balance_end_real"],
                places=2,
            )

    def test_parse_file_invalid_balance_A(self):
        data_file = (
            base64.b64decode(self.import_wizard_A.statement_file)
            .decode("utf-8")
            .splitlines()
        )
        # artificially corrupt closing balance line
        data_file[3] = "Solde en fin de période;;;;9999,99;"
        res = self.import_wizard_A._check_file(data_file)
        self.assertTrue(res, False)

    def test_parse_file_invalid_balance_B(self):
        data_file = (
            base64.b64decode(self.import_wizard_B.statement_file)
            .decode("utf-8")
            .splitlines()
        )
        # artificially corrupt closing balance line
        data_file[3] = "Solde en fin de période;;;9999,99;"
        res = self.import_wizard_B._check_file(data_file)
        self.assertTrue(res, False)

    def test_parse_file_invalid_balance_C(self):
        data_file = (
            base64.b64decode(self.import_wizard_C.statement_file)
            .decode("utf-8")
            .splitlines()
        )
        # artificially corrupt closing balance line
        data_file[3] = "Solde en fin de période;;;;9999,99"
        res = self.import_wizard_C._check_file(data_file)
        self.assertTrue(res, False)
