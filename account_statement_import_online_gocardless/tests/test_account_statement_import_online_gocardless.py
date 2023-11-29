# Copyright 2023 Tecnativa - Pedro M.Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from unittest import mock

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import common

_module_ns = "odoo.addons.account_statement_import_online_gocardless"
_provider_class = (
    _module_ns + ".models.online_bank_statement_provider.OnlineBankStatementProvider"
)


class TestAccountBankAccountStatementImportOnlineGocardless(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.now = fields.Datetime.now()
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_eur.write({"active": True})
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "GoCardless Bank Test",
                "type": "bank",
                "code": "GCB",
                "currency_id": cls.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "gocardless",
            }
        )
        cls.provider = cls.journal.online_bank_statement_provider_id
        cls.provider.write(
            {
                "statement_creation_mode": "monthly",
                "gocardless_account_id": "SANDBOXFINANCE_SFIN0000",
                "gocardless_requisition_expiration": cls.now + relativedelta(days=30),
            }
        )
        cls.return_value = {  # GoCardless sample return
            "transactions": {
                "booked": [
                    {
                        "transactionId": "2020103000624289-1",
                        "debtorName": "MON MOTHMA",
                        "debtorAccount": {"iban": "GL53SAFI055151515"},
                        "transactionAmount": {"currency": "EUR", "amount": "45.00"},
                        "bookingDate": "2020-10-30",
                        "valueDate": "2020-10-30",
                        "remittanceInformationUnstructured": (
                            "For the support of Restoration of the Republic foundation"
                        ),
                    },
                    {
                        "transactionId": "2020111101899195-1",
                        "transactionAmount": {"currency": "EUR", "amount": "-15.00"},
                        "bankTransactionCode": "PMNT",
                        "bookingDate": "2020-11-11",
                        "valueDate": "2020-11-11",
                        "remittanceInformationUnstructured": "PAYMENT Alderaan Coffe",
                    },
                ],
                "pending": [
                    {
                        "transactionAmount": {"currency": "EUR", "amount": "-10.00"},
                        "valueDate": "2020-11-03",
                        "remittanceInformationUnstructured": (
                            "Reserved PAYMENT Emperor's Burgers"
                        ),
                    }
                ],
            }
        }
        cls.mock_transaction = lambda cls: mock.patch(
            _provider_class + "._gocardless_request_transactions",
            return_value=cls.return_value,
        )

    def test_mocked_gocardless(self):
        vals = {
            "provider_ids": self.provider.ids,
            "date_since": "2020-10-30",
            "date_until": "2020-11-11",
        }
        wizard = (
            self.env["online.bank.statement.pull.wizard"]
            .with_context(
                active_model="account.journal",
                active_id=self.journal.id,
            )
            .create(vals)
        )
        with self.mock_transaction():
            wizard.action_pull()
        statements = self.env["account.bank.statement"].search(
            [("journal_id", "=", self.journal.id)]
        )
        self.assertEqual(len(statements), 2)
        lines = statements.line_ids.sorted(lambda x: x.date)
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines.mapped("amount"), [45.0, -15.0])
