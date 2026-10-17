# Copyright 2023 Tecnativa - Pedro M.Baeza
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from unittest import mock

import requests
from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

_module_ns = "odoo.addons.account_statement_import_online_gocardless"
_provider_class = (
    _module_ns + ".models.online_bank_statement_provider.OnlineBankStatementProvider"
)


class TestAccountBankAccountStatementImportOnlineGocardless(common.TransactionCase):
    def test_http_preserves_requests_and_errors(self):
        self.provider.api_base = "http://untrusted.invalid"
        for method, status, payload in (
            ("get", 200, {"institutions": []}),
            ("post", 201, {"access": "dummy-token"}),
            ("get", 429, {"detail": "Test rate limit"}),
        ):
            response = requests.Response()
            response.status_code = status
            response._content = json.dumps(payload).encode()
            with (
                self.subTest(method=method, status=status),
                mock.patch.object(
                    type(self.provider),
                    "_gocardless_get_token",
                    return_value="dummy-token",
                ),
                mock.patch("requests.sessions.get_environ_proxies", return_value={}),
                mock.patch(
                    "requests.adapters.HTTPAdapter.send", return_value=response
                ) as transport,
            ):
                if status == 429:
                    with self.assertRaisesRegex(UserError, "Test rate limit"):
                        self.provider._gocardless_request("institutions")
                else:
                    _, data = self.provider._gocardless_request(
                        "institutions",
                        request_type=method,
                        params={"country": "GB"},
                        data="dummy-body",
                        basic_auth=method == "post",
                    )
                    self.assertEqual(data, payload)
                transport.assert_called_once()
                request = transport.call_args.args[0]
                self.assertEqual(request.method, method.upper())
                self.assertTrue(
                    request.url.startswith(
                        "https://bankaccountdata.gocardless.com/api/v2/institutions/"
                    )
                )
                self.assertEqual(transport.call_args.kwargs["timeout"], 60)
                self.assertEqual(
                    request.headers.get("Authorization"),
                    None if method == "post" else "Bearer dummy-token",
                )
                if status != 429:
                    self.assertIn("country=GB", request.url)
                    self.assertEqual(request.body, "dummy-body")

    def test_http_rejects_untrusted_joined_endpoints(self):
        for endpoint in (
            "http://127.0.0.1",
            "http://[::1]",
            "http://169.254.169.254/latest",
            "//untrusted.invalid",
            "https://untrusted.invalid",
            "https://bankaccountdata.gocardless.com.evil.invalid",
            "https://evil@bankaccountdata.gocardless.com",
            "https://bankaccountdata.gocardless.com@evil.invalid",
            "https://bankaccountdata.gocardless.com:444",
            "https://bankaccountdata.gocardless.com:invalid",
            "https://bankaccountdata.gocardless.com#fragment",
        ):
            with (
                self.subTest(endpoint=endpoint),
                mock.patch.object(
                    type(self.provider), "_gocardless_get_headers"
                ) as headers,
                mock.patch("requests.get") as request,
                self.assertRaisesRegex(UserError, "official GoCardless HTTPS"),
            ):
                try:
                    self.provider._gocardless_request(endpoint)
                finally:
                    headers.assert_not_called()
                    request.assert_not_called()

    def test_http_rejects_get_and_token_redirects(self):
        for status in (301, 302, 303, 307, 308):
            for target in ("http://127.0.0.1/private", "https://untrusted.invalid/"):
                for method in ("get", "post"):
                    response = requests.Response()
                    response.status_code = status
                    response.headers["Location"] = target
                    response._content = b"{}"
                    response.request = requests.Request(
                        method.upper(), "https://bankaccountdata.gocardless.com/api/v2/"
                    ).prepare()
                    response.url = response.request.url
                    with (
                        self.subTest(status=status, target=target, method=method),
                        mock.patch.object(
                            type(self.provider),
                            "_gocardless_get_token",
                            return_value="dummy-token",
                        ),
                        mock.patch(
                            "requests.sessions.get_environ_proxies", return_value={}
                        ),
                        mock.patch(
                            "requests.adapters.HTTPAdapter.send",
                            side_effect=[response, AssertionError("Redirect followed")],
                        ) as transport,
                        self.assertRaisesRegex(UserError, "redirects are not allowed"),
                    ):
                        try:
                            self.provider._gocardless_request(
                                "token/new" if method == "post" else "institutions",
                                request_type=method,
                                data='{"secret_key":"dummy-secret"}'
                                if method == "post"
                                else None,
                                basic_auth=method == "post",
                            )
                        finally:
                            transport.assert_called_once()

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
