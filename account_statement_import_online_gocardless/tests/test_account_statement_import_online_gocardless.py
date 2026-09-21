# Copyright 2023 Tecnativa - Pedro M.Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest import mock

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
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
        cls.journal.company_id.country_id = cls.env.ref("base.es")
        cls.journal.bank_account_id = cls.env["res.partner.bank"].create(
            {
                "acc_number": "GOCARDLESS-TEST-ACCOUNT",
                "partner_id": cls.journal.company_id.partner_id.id,
                "company_id": cls.journal.company_id.id,
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

    def test_select_bank_token_lifecycle(self):
        institutions = [{"id": "TEST_BANK", "name": "Test Bank", "countries": ["ES"]}]
        for refresh_valid in (False, True):
            with self.subTest(refresh_valid=refresh_valid):
                self.provider.write(
                    {
                        "username": "test-secret-id",
                        "password": "test-secret-key",
                        "gocardless_token": "expired-access",
                        "gocardless_token_expiration": self.now - relativedelta(days=1),
                        "gocardless_refresh_token": "test-refresh",
                        "gocardless_refresh_expiration": self.now
                        + relativedelta(days=1 if refresh_valid else -1),
                    }
                )
                token_data = {"access": "new-access", "access_expires": 86400}
                if not refresh_valid:
                    token_data.update(refresh="new-refresh", refresh_expires=2592000)
                with mock.patch(
                    _module_ns + ".models.online_bank_statement_provider.requests.post",
                    return_value=mock.Mock(
                        status_code=200, text=json.dumps(token_data)
                    ),
                ) as post, mock.patch(
                    _module_ns + ".models.online_bank_statement_provider.requests.get",
                    return_value=mock.Mock(
                        status_code=200, text=json.dumps(institutions)
                    ),
                ) as get:
                    action = self.provider.action_select_gocardless_bank()
                self.assertEqual(action["context"]["institutions"], institutions)
                self.assertEqual(action["context"]["country"], "ES")
                self.assertTrue(
                    post.call_args.args[0].endswith(
                        "/token/refresh/" if refresh_valid else "/token/new/"
                    )
                )
                self.assertEqual(
                    json.loads(post.call_args.kwargs["data"]),
                    {"refresh": "test-refresh"}
                    if refresh_valid
                    else {
                        "secret_id": "test-secret-id",
                        "secret_key": "test-secret-key",
                    },
                )
                self.assertEqual(
                    get.call_args.kwargs["headers"]["Authorization"],
                    "Bearer new-access",
                )
                self.assertEqual(
                    self.provider.gocardless_refresh_token,
                    "test-refresh" if refresh_valid else "new-refresh",
                )

    def test_select_bank_authentication_error(self):
        self.provider.gocardless_token = False
        with mock.patch(
            _module_ns + ".models.online_bank_statement_provider.requests.post",
            return_value=mock.Mock(
                status_code=401, text='{"detail": "Invalid secret"}'
            ),
        ), mock.patch(
            _module_ns + ".models.online_bank_statement_provider.requests.get"
        ) as get:
            with self.assertRaisesRegex(UserError, "Invalid secret"):
                self.provider.action_select_gocardless_bank()
            get.assert_not_called()

    def test_select_bank_institutions_error(self):
        self.provider.write(
            {
                "gocardless_token": "valid-access",
                "gocardless_token_expiration": self.now + relativedelta(days=1),
            }
        )
        for status in (401, 403, 429, 500):
            with self.subTest(status=status), mock.patch(
                _module_ns + ".models.online_bank_statement_provider.requests.get",
                return_value=mock.Mock(
                    status_code=status, text='{"detail": "Institutions unavailable"}'
                ),
            ), mock.patch(
                _module_ns + ".models.online_bank_statement_provider.requests.post"
            ) as post:
                with self.assertRaisesRegex(UserError, "Institutions unavailable"):
                    self.provider.action_select_gocardless_bank()
                post.assert_not_called()

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
