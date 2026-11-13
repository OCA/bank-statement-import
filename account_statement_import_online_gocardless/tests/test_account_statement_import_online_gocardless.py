# Copyright 2023 Tecnativa - Pedro M.Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest import mock

import requests
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common
from odoo.tools import mute_logger

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
        bank_account = cls.env["res.partner.bank"].create(
            {
                "acc_number": "NL77ABNA0574908765",
                "partner_id": cls.env.ref("base.main_partner").id,
                "company_id": cls.env.ref("base.main_company").id,
                "bank_id": cls.env.ref("base.res_bank_1").id,
            }
        )
        cls.journal = cls.env["account.journal"].create(
            {
                "name": "GoCardless Bank Test",
                "type": "bank",
                "code": "GCB",
                "currency_id": cls.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "gocardless",
                "bank_account_id": bank_account.id,
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
        cls.request_requisition_value = {
            "accounts": ["ACCOUNT-ID-1"],
            "agreement": "TEST-AGREEMENT-ID",
        }
        cls.mock_requisition = lambda cls: mock.patch(
            _provider_class + "._gocardless_request_requisition",
            return_value=cls.request_requisition_value,
        )
        cls.request_account_value = {
            "id": "ACCOUNT-ID-1",
            "iban": "nl77abna0574908765",
        }
        cls.mock_account = lambda cls: mock.patch(
            _provider_class + "._gocardless_request_account",
            return_value=cls.request_account_value,
        )
        cls.request_agreement_value = {
            "id": "TEST-AGREEMENT-ID",
            "accepted": cls.now.strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "access_valid_for_days": 30,
        }
        cls.mock_agreement = lambda cls: mock.patch(
            _provider_class + "._gocardless_request_agreement",
            return_value=cls.request_agreement_value,
        )

    def test_mocked_gocardless(self):
        vals = {
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

    def test_provider_gocardless_finish_requisition(self):
        with self.mock_requisition(), self.mock_account(), self.mock_agreement():
            res = self.provider._gocardless_finish_requisition(dry=True)
            self.assertTrue(res, "Bank account not found!")

    def _http_transaction_response(self, status):
        response = requests.Response()
        response.status_code = status
        response.url = (
            "https://bankaccountdata.gocardless.com/api/v2/accounts/"
            f"{self.provider.gocardless_account_id}/transactions/"
        )
        payload = (
            {"transactions": {"booked": []}}
            if status == 200
            else {"detail": "fabricated refusal"}
        )
        response._content = json.dumps(payload).encode()
        return response

    def test_transaction_http_errors_keep_the_scheduled_checkpoint(self):
        since = fields.Datetime.to_datetime("2020-10-01 00:00:00")
        until = fields.Datetime.to_datetime("2020-11-01 00:00:00")
        for status in (200, 401, 500):
            with self.subTest(status=status):
                self.provider.write(
                    {
                        "tz": "UTC",
                        "last_successful_run": since,
                        "next_run": until,
                        "gocardless_token": "fabricated-access-token",
                        "gocardless_token_expiration": self.now + relativedelta(days=1),
                    }
                )
                response = self._http_transaction_response(status)
                with (
                    mock.patch(
                        _module_ns
                        + ".models.online_bank_statement_provider.requests.get",
                        return_value=response,
                    ) as request,
                    mute_logger(
                        "odoo.addons.account_statement_import_online.models.online_bank_statement_provider"
                    ),
                ):
                    self.provider.with_context(scheduled=True)._pull(since, until)
                self.assertEqual(
                    self.provider.last_successful_run, until if status == 200 else since
                )
                self.assertGreater(self.provider.next_run, until)
                request.assert_called_once()
                self.assertFalse(
                    self.env["account.bank.statement"].search(
                        [("journal_id", "=", self.journal.id)]
                    )
                )

    def test_transaction_http_errors_reach_manual_pull(self):
        since = fields.Datetime.to_datetime("2020-10-01 00:00:00")
        until = fields.Datetime.to_datetime("2020-11-01 00:00:00")
        self.provider.write(
            {
                "tz": "UTC",
                "gocardless_token": "fabricated-access-token",
                "gocardless_token_expiration": self.now + relativedelta(days=1),
            }
        )
        for status in (401, 500):
            with self.subTest(status=status):
                response = self._http_transaction_response(status)
                with (
                    mock.patch(
                        _module_ns
                        + ".models.online_bank_statement_provider.requests.get",
                        return_value=response,
                    ),
                    self.assertRaises(UserError) as raised,
                ):
                    self.provider._pull(since, until)
                self.assertIn(f"HTTP {status}", str(raised.exception))
                self.assertIn("fabricated refusal", str(raised.exception))

    def test_expired_consent_keeps_the_scheduled_checkpoint(self):
        since = fields.Datetime.to_datetime("2020-10-01 00:00:00")
        until = fields.Datetime.to_datetime("2020-11-01 00:00:00")
        self.provider.write(
            {
                "tz": "UTC",
                "last_successful_run": since,
                "next_run": until,
                "gocardless_requisition_expiration": self.now - relativedelta(days=1),
            }
        )
        with (
            mock.patch(
                _module_ns + ".models.online_bank_statement_provider.requests.get"
            ) as request,
            mute_logger(
                "odoo.addons.account_statement_import_online.models.online_bank_statement_provider"
            ),
        ):
            self.provider.with_context(scheduled=True)._pull(since, until)
        request.assert_not_called()
        self.assertEqual(self.provider.last_successful_run, since)
        self.assertGreater(self.provider.next_run, until)
        self.assertFalse(
            self.env["account.bank.statement"].search(
                [("journal_id", "=", self.journal.id)]
            )
        )
        self.assertTrue(
            any(
                "renew the authorization" in (message.body or "")
                for message in self.provider.message_ids
            )
        )

    def test_expired_consent_reaches_the_manual_pull_as_a_user_error(self):
        self.provider.gocardless_requisition_expiration = self.now - relativedelta(
            days=1
        )
        with (
            mock.patch(
                _module_ns + ".models.online_bank_statement_provider.requests.get"
            ) as request,
            self.assertRaises(UserError) as raised,
        ):
            self.provider._pull(
                fields.Datetime.to_datetime("2020-10-01 00:00:00"),
                fields.Datetime.to_datetime("2020-11-01 00:00:00"),
            )
        request.assert_not_called()
        self.assertIn("renew the authorization", str(raised.exception))
