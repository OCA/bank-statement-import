# Copyright 2020 Florent de Labarre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest import mock

from odoo import fields
from odoo.tests import common

_module_ns = "odoo.addons.account_statement_import_online_ponto"
_provider_class = (
    _module_ns
    + ".models.online_bank_statement_provider_ponto"
    + ".OnlineBankStatementProviderPonto"
)


class TestAccountBankAccountStatementImportOnlineQonto(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.AccountJournal = self.env["account.journal"]
        self.ResPartnerBank = self.env["res.partner.bank"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

        self.bank_account = self.ResPartnerBank.create(
            {
                "acc_number": "FR0214508000302245362775K46",
                "partner_id": self.env.user.company_id.partner_id.id,
            }
        )
        self.journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "ponto",
                "bank_account_id": self.bank_account.id,
            }
        )
        self.provider = self.journal.online_bank_statement_provider_id

        self.mock_header = lambda: mock.patch(
            _provider_class + "._ponto_header",
            return_value={
                "Accept": "application/json",
                "Authorization": "Bearer --TOKEN--",
            },
        )

        self.mock_account_ids = lambda: mock.patch(
            _provider_class + "._ponto_get_account_ids",
            return_value={"FR0214508000302245362775K46": "id"},
        )
        self.mock_synchronisation = lambda: mock.patch(
            _provider_class + "._ponto_synchronisation",
            return_value=None,
        )

        self.mock_transaction = lambda: mock.patch(
            _provider_class + "._ponto_get_transaction",
            return_value=[
                {
                    "type": "transaction",
                    "relationships": {
                        "account": {
                            "links": {"related": "https://api.myponto.com/accounts/"},
                            "data": {
                                "type": "account",
                                "id": "fd3d5b1d-fca9-4310-a5c8-76f2a9dc7c75",
                            },
                        }
                    },
                    "id": "701ab965-21c4-46ca-b157-306c0646e0e2",
                    "attributes": {
                        "valueDate": "2019-11-18T00:00:00.000Z",
                        "remittanceInformationType": "unstructured",
                        "remittanceInformation": "Minima vitae totam!",
                        "executionDate": "2019-11-20T00:00:00.000Z",
                        "description": "Wire transfer",
                        "currency": "EUR",
                        "counterpartReference": "BE26089479973169",
                        "counterpartName": "Osinski Group",
                        "amount": 6.08,
                    },
                },
                {
                    "type": "transaction",
                    "relationships": {
                        "account": {
                            "links": {"related": "https://api.myponto.com/accounts/"},
                            "data": {
                                "type": "account",
                                "id": "fd3d5b1d-fca9-4310-a5c8-76f2a9dc7c75",
                            },
                        }
                    },
                    "id": "9ac50483-16dc-4a82-aa60-df56077405cd",
                    "attributes": {
                        "valueDate": "2019-11-04T00:00:00.000Z",
                        "remittanceInformationType": "unstructured",
                        "remittanceInformation": "Quia voluptatem blanditiis.",
                        "executionDate": "2019-11-06T00:00:00.000Z",
                        "description": "Wire transfer",
                        "currency": "EUR",
                        "counterpartReference": "BE97201830401438",
                        "counterpartName": "Stokes-Miller",
                        "amount": 5.48,
                    },
                },
                {
                    "type": "transaction",
                    "relationships": {
                        "account": {
                            "links": {"related": "https://api.myponto.com/accounts/"},
                            "data": {
                                "type": "account",
                                "id": "fd3d5b1d-fca9-4310-a5c8-76f2a9dc7c75",
                            },
                        }
                    },
                    "id": "b21a6c65-1c52-4ba6-8cbc-127d2b2d85ff",
                    "attributes": {
                        "valueDate": "2019-11-04T00:00:00.000Z",
                        "remittanceInformationType": "unstructured",
                        "remittanceInformation": "Laboriosam repelo?",
                        "executionDate": "2019-11-04T00:00:00.000Z",
                        "description": "Wire transfer",
                        "currency": "EUR",
                        "counterpartReference": "BE10325927501996",
                        "counterpartName": "Strosin-Veum",
                        "amount": 5.83,
                    },
                },
            ],
        )

    def test_ponto(self):
        with self.mock_transaction(), self.mock_header(), self.mock_synchronisation(), self.mock_account_ids():  # noqa: B950
            lines, statement_values = self.provider._obtain_statement_data(
                datetime(2019, 11, 3),
                datetime(2019, 11, 17),
            )

        self.assertEqual(len(lines), 3)
