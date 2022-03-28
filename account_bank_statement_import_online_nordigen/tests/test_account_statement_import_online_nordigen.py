# Copyright (C) 2022 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest import mock

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import common

SAMPLE_ACCOUNT_NUMBER_1 = "GL3343697694912188"
SAMPLE_ACCOUNT_NUMBER_2 = "GL0865354374424724"
SANDBOX_INSTITUTION_ID = "SANDBOXFINANCE_SFIN0000"

_module_ns = "odoo.addons.account_bank_statement_import_online_nordigen"
_provider_class = (
    _module_ns
    + ".models.online_bank_statement_provider_nordigen"
    + ".OnlineBankStatementProviderNordigen"
)
_provider_controller_class = _module_ns + ".controllers.main" + ".NordigenController"


class TestAccountBankAccountStatementImportOnlineNordigen(common.TransactionCase):
    def setUp(self):
        super().setUp()
        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.AccountJournal = self.env["account.journal"]
        self.ResPartnerBank = self.env["res.partner.bank"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

        self.bank_account = self.ResPartnerBank.create(
            {
                "acc_number": SAMPLE_ACCOUNT_NUMBER_1,
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
                "online_bank_statement_provider": "nordigen",
                "bank_account_id": self.bank_account.id,
            }
        )
        self.provider = self.journal.online_bank_statement_provider_id
        self.provider.nordigen_last_requisition_id = "TEST-REQUISITION-ID"
        plus_90_days = relativedelta(days=90)
        self.provider.nordigen_last_requisition_expiration = self.now + plus_90_days
        self.provider.nordigen_account_id = "TEST-ACCOUNT-ID"
        self.mock_header = lambda: mock.patch(
            _provider_class + "._get_nordigen_headers",
            return_value={
                "Accept": "application/json",
                "Authorization": "Bearer --TOKEN--",
            },
        )
        self.mock_update_token = lambda: mock.patch(
            _provider_class + "._update_token_nordigen", return_value=None,
        )
        self.mock_institutions = lambda: mock.patch(
            _provider_class + "._get_nordigen_institutions",
            return_value=[
                {
                    "id": SANDBOX_INSTITUTION_ID,
                    "name": "SANBOX BANK",
                    "bic": "XXXXXXXXXX",
                    "transaction_total_days": "90",
                    "countries": ["ES"],
                    "logo": "https://awesomeurl.com/logo.png",
                },
            ],
        )
        self.mock_controller = lambda: mock.patch(
            _provider_controller_class + ".nordigen_response", return_value=True
        )
        self.mock_transactions = lambda: mock.patch(
            _provider_class + "._nordigen_get_transactions",
            return_value={
                "transactions": {
                    "booked": [
                        {
                            "bankTransactionCode": "PMNT",
                            "bookingDate": "2022-03-27",
                            "debtorAccount": {"iban": "GL3343697694912188"},
                            "debtorName": "MON MOTHMA",
                            "remittanceInformationUnstructured": "TEST",
                            "transactionAmount": {"amount": "45.00", "currency": "EUR"},
                            "transactionId": "2022032701927907-1",
                            "valueDate": "2022-03-27",
                        },
                        {
                            "bankTransactionCode": "PMNT",
                            "bookingDate": "2022-03-27",
                            "debtorAccount": {"iban": "GL3343697694912188"},
                            "debtorName": "MON MOTHMA",
                            "remittanceInformationUnstructured": "TEST",
                            "transactionAmount": {"amount": "45.00", "currency": "EUR"},
                            "transactionId": "2022032701927901-1",
                            "valueDate": "2022-03-27",
                        },
                        {
                            "bankTransactionCode": "PMNT",
                            "bookingDate": "2022-03-27",
                            "remittanceInformationUnstructured": "TEST",
                            "transactionAmount": {
                                "amount": "-15.00",
                                "currency": "EUR",
                            },
                            "transactionId": "2022032701927905-1",
                            "valueDate": "2022-03-27",
                        },
                        {
                            "bankTransactionCode": "PMNT",
                            "bookingDate": "2022-03-27",
                            "remittanceInformationUnstructured": "TEST",
                            "transactionAmount": {
                                "amount": "-15.00",
                                "currency": "EUR",
                            },
                            "transactionId": "2022032701927908-1",
                            "valueDate": "2022-03-27",
                        },
                        {
                            "bankTransactionCode": "PMNT",
                            "bookingDate": "2022-03-27",
                            "debtorAccount": {"iban": "GL3343697694912188"},
                            "debtorName": "MON MOTHMA",
                            "remittanceInformationUnstructured": "TEST",
                            "transactionAmount": {"amount": "45.00", "currency": "EUR"},
                            "transactionId": "2022032701927904-1",
                            "valueDate": "2022-03-27",
                        },
                        {
                            "bankTransactionCode": "PMNT",
                            "bookingDate": "2022-03-27",
                            "remittanceInformationUnstructured": "TEST",
                            "transactionAmount": {
                                "amount": "-15.00",
                                "currency": "EUR",
                            },
                            "transactionId": "2022032701927902-1",
                            "valueDate": "2022-03-27",
                        },
                    ]
                }
            },
        )

    def test_nordigen(self):
        with self.mock_header(), self.mock_update_token(), self.mock_transactions():  # noqa: B950
            lines, statement_values = self.provider._obtain_statement_data(
                datetime(2022, 3, 27), datetime(2022, 3, 27),
            )
            self.assertIsInstance(lines, dict)
            self.assertEqual(len(lines.get("transactions", {}).get("booked", [])), 6)

            headers = self.provider._get_nordigen_headers(token="TEST")
            self.assertIsInstance(headers, dict)
            self.assertEqual(headers.get("Authorization"), "Bearer %s" % "TEST")

            self.provider.nordigen_reset_last_identifier()
            self.assertFalse(self.provider.nordigen_last_requisition_id)
            self.assertFalse(self.provider.nordigen_last_requisition_ref)
            self.assertFalse(self.provider.nordigen_last_requisition_expiration)

            self.provider.journal_id.bank_account_id = False
            with self.assertRaises(Exception):
                self.provider._check_bank_account_nordigen()


class TestHttpNordigen(common.HttpCase):
    def setUp(self):
        super(TestHttpNordigen, self).setUp()
        self.domain = "http://127.0.0.1:8069"
        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref("base.EUR")
        self.AccountJournal = self.env["account.journal"]
        self.ResPartnerBank = self.env["res.partner.bank"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

        self.bank_account = self.ResPartnerBank.create(
            {
                "acc_number": SAMPLE_ACCOUNT_NUMBER_2,
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
                "online_bank_statement_provider": "nordigen",
                "bank_account_id": self.bank_account.id,
            }
        )
        self.provider = self.journal.online_bank_statement_provider_id
        self.provider.nordigen_last_requisition_id = "TEST-REQUISITION-ID"
        self.provider.nordigen_last_requisition_ref = "TEST-REQUISITION-ID"
        plus_90_days = relativedelta(days=90)
        self.provider.nordigen_last_requisition_expiration = self.now + plus_90_days
        self.provider.nordigen_account_id = "TEST-ACCOUNT-ID"
        self.mock_update_request = lambda: mock.patch(
            _provider_class + ".update_nordigen_request", return_value=True,
        )
        self.mock_update_token = lambda: mock.patch(
            _provider_class + "._update_token_nordigen", return_value=None,
        )

    def test_nordigen_response(self):
        with self.mock_update_token():
            res = self.url_open(
                self.domain + "/nordigen/response",
                data={"ref": self.provider.nordigen_last_requisition_id},
            )
            self.assertEqual(res.status_code, 200)
            self.assertIn("model=online.bank.statement.provider", res.url)
            self.assertIn("id=" + str(self.provider.id), res.url)
