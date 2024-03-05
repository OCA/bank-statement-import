import base64
import datetime

from odoo.modules.module import get_module_resource
from odoo.tests.common import TransactionCase

from ..components.account_statement_import_process import EdiBankStatementImportProcess


class MockExchangeRecord:
    __slots__ = ["exchange_file", "exchange_filename"]

    def __init__(self, exchange_file, exchange_filename: str):
        self.exchange_file = exchange_file
        self.exchange_filename = exchange_filename


class MockWorkContext:
    __slots__ = ["env"]

    def __init__(self, env):
        self.env = env


class EdiBankStatementImportProcessTest(EdiBankStatementImportProcess):
    _name = "edi.input.process.bank.statement.import.test"
    _inherit = "edi.input.process.bank.statement.import"

    def __init__(self, exchange_record: MockExchangeRecord, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.exchange_record = exchange_record


class TestAccountStatementImportProcess(TransactionCase):
    def setUp(self):
        super(TestAccountStatementImportProcess, self).setUp()

        bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "NL12ABCD3456789012",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        self.env["account.journal"].create(
            {
                "name": "Bank Journal",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": self.env.ref("base.EUR").id,
            }
        )

    def test_account_statement_import_process(self):
        filename = "camt053"
        stmt_id = "5678ABC/1"
        self._assert_account_statement_import_count(0, filename)

        data = get_module_resource(
            "account_statement_import_sftp", "test_files", filename
        )

        with open(data, "rb") as datafile:
            file = base64.b64encode(datafile.read())

            mock_exchange_record = MockExchangeRecord(file, filename)
            mock_work_context = MockWorkContext(self.env)

            EdiBankStatementImportProcessTest(
                mock_exchange_record,
                mock_work_context,
            ).process()

            elt = self.env["account.bank.statement"].search(
                [("name", "=", stmt_id)],
            )

            tot = 75000.0
            diff = -1200.0
            self.assertEqual("5678ABC/1", elt.name)
            self.assertEqual(tot, elt.balance_start)
            self.assertEqual(tot + diff, elt.balance_end)
            self.assertEqual(datetime.date(2024, 3, 2), elt.date)
            self.assertEqual("open", elt.state)

            lines = elt.line_ids
            self.assertEqual(diff, lines[0].amount)

            self._assert_account_statement_import_count(1, filename)

    def _assert_account_statement_import_count(self, count, filename):
        self.assertEqual(
            count,
            self.env["account.statement.import"].search_count(
                [("statement_filename", "=", filename)]
            ),
        )
