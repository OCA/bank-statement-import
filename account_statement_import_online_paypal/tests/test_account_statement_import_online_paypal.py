# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2021-2022 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from datetime import datetime, timedelta
from decimal import Decimal
from unittest import mock
from unittest.mock import patch
from urllib.error import HTTPError

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

from ..models.online_bank_statement_provider_paypal import _paypal_payment_keys

_module_ns = "odoo.addons.account_statement_import_online_paypal"
_provider_class = (
    _module_ns
    + ".models.online_bank_statement_provider_paypal"
    + ".OnlineBankStatementProviderPayPal"
)


class FakeHTTPError(HTTPError):
    def __init__(self, content):
        self.content = content

    # pylint: disable=method-required-super
    def read(self):
        return self.content.encode("utf-8")


class UrlopenRetValMock:
    def __init__(self, content, throw=False):
        self.content = content
        self.throw = throw

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    # pylint: disable=method-required-super
    def read(self):
        if self.throw:
            raise FakeHTTPError(self.content)
        return self.content.encode("utf-8")


ODOO_DAY = datetime.combine(datetime.now().date(), datetime.min.time()) - timedelta(
    days=1
)


ODOO_MODULE = (
    "odoo.addons.account_statement_import_online_paypal.models"
    ".online_bank_statement_provider_paypal.OnlineBankStatementProviderPayPal"
)


def _odoo_transaction(transaction_id, order_id=None):
    info = {
        "transaction_id": transaction_id,
        "transaction_event_code": "T0006",
        "transaction_updated_date": ODOO_DAY + timedelta(hours=10),
        "transaction_amount": {"currency_code": "USD", "value": "10.00"},
        "fee_amount": {"currency_code": "USD", "value": "-0.50"},
        "available_balance": {"currency_code": "USD", "value": "100.00"},
        "transaction_subject": "Order",
    }
    if order_id:
        info["paypal_reference_id"] = order_id
        info["paypal_reference_id_type"] = "ODR"
    return {"transaction_info": info, "payer_info": {}, "cart_info": {}}


class TestAccountBankAccountStatementImportOnlinePayPal(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.odoo_journal = cls.env["account.journal"].create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PODOO",
                "bank_statements_source": "online",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.odoo_partner = cls.env["res.partner"].create({"name": "Customer"})
        cls.odoo_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "paypal",
                "username": "client_id",
                "password": "secret",
                "journal_id": cls.odoo_journal.id,
                "paypal_skip_website_payments": True,
            }
        )
        cls.odoo_transactions = [
            _odoo_transaction("CAPTURE1"),
            _odoo_transaction("CAPTURE2", order_id="ORDER2"),
            _odoo_transaction("CAPTURE3"),
        ]

    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.now_isoformat = self.now.isoformat() + "+0000"
        self.today = datetime(self.now.year, self.now.month, self.now.day)
        self.today_isoformat = self.today.isoformat() + "+0000"
        self.today_timestamp = str(int(self.today.timestamp()))
        self.yesterday = self.today - relativedelta(days=1)
        self.yesterday_isoformat = self.yesterday.isoformat() + "+0000"
        self.yesterday_timestamp = str(int(self.yesterday.timestamp()))
        self.currency_eur = self.env.ref("base.EUR")
        self.currency_usd = self.env.ref("base.USD")
        self.AccountJournal = self.env["account.journal"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]

        Provider = self.OnlineBankStatementProvider
        self.paypal_parse_transaction = lambda payload: (
            Provider._paypal_transaction_to_lines(
                Provider._paypal_preparse_transaction(
                    json.loads(
                        payload,
                        parse_float=Decimal,
                    )
                )
            )
        )
        self.mock_token = lambda: mock.patch(
            _provider_class + "._paypal_get_token",
            return_value="--TOKEN--",
        )

    def test_good_token(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads(
            """{
    "scope": "https://uri.paypal.com/services/reporting/search/read",
    "access_token": "---TOKEN---",
    "token_type": "Bearer",
    "app_id": "APP-1234567890",
    "expires_in": 32400,
    "nonce": "---NONCE---"
}""",
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_response,
        ):
            token = provider._paypal_get_token()
        self.assertEqual(token, "---TOKEN---")

    def test_bad_token_scope(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads(
            """{
    "scope": "openid https://uri.paypal.com/services/applications/webhooks",
    "access_token": "---TOKEN---",
    "token_type": "Bearer",
    "app_id": "APP-1234567890",
    "expires_in": 32400,
    "nonce": "---NONCE---"
}""",
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_response,
        ):
            with self.assertRaisesRegex(
                UserError, "PayPal App features are configured incorrectly!"
            ):
                provider._paypal_get_token()

    def test_bad_token_type(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads(
            """{
    "scope": "https://uri.paypal.com/services/reporting/search/read",
    "access_token": "---TOKEN---",
    "token_type": "NotBearer",
    "app_id": "APP-1234567890",
    "expires_in": 32400,
    "nonce": "---NONCE---"
}""",
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_response,
        ):
            with self.assertRaisesRegex(UserError, "Invalid token type!"):
                provider._paypal_get_token()

    def test_no_token(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads(
            """{
        "scope": "https://uri.paypal.com/services/reporting/search/read",
        "token_type": "Bearer",
        "app_id": "APP-1234567890",
        "expires_in": 32400,
        "nonce": "---NONCE---"
    }""",
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_response,
        ):
            with self.assertRaisesRegex(
                UserError, "Failed to acquire token using Client ID and Secret!"
            ):
                provider._paypal_get_token()

    def test_no_data_on_monday(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response_1 = UrlopenRetValMock(
            """{
    "debug_id": "eec890ebd5798",
    "details": "xxxxxx",
    "links": "xxxxxx",
    "message": "Data for the given start date is not available.",
    "name": "INVALID_REQUEST"
}""",
            throw=True,
        )
        mocked_response_2 = UrlopenRetValMock(
            f"""{{
    "balances": [
        {{
            "currency": "EUR",
            "primary": true,
            "total_balance": {{
                "currency_code": "EUR",
                "value": "0.75"
            }},
            "available_balance": {{
                "currency_code": "EUR",
                "value": "0.75"
            }},
            "withheld_balance": {{
                "currency_code": "EUR",
                "value": "0.00"
            }}
        }}
    ],
    "account_id": "1234567890",
    "as_of_time": "{self.now_isoformat}",
    "last_refresh_time": "{self.now_isoformat}"
}}"""
        )
        with (
            mock.patch(
                _provider_class + "._paypal_urlopen",
                side_effect=[mocked_response_1, mocked_response_2],
            ),
            self.mock_token(),
        ):
            data = provider.with_context(
                test_account_statement_import_online_paypal_monday=True,
            )._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertEqual(data, ([], {"balance_start": 0.75, "balance_end_real": 0.75}))

    def test_error_handling_1(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = UrlopenRetValMock(
            """{
    "message": "MESSAGE",
    "name": "ERROR"
}""",
            throw=True,
        )
        with mock.patch(
            _provider_class + "._paypal_urlopen",
            return_value=mocked_response,
        ):
            with self.assertRaises(UserError):
                provider._paypal_retrieve("https://url", "")

    def test_error_handling_2(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = UrlopenRetValMock(
            """{
    "error_description": "ERROR DESCRIPTION",
    "error": "ERROR"
}""",
            throw=True,
        )
        with mock.patch(
            _provider_class + "._paypal_urlopen",
            return_value=mocked_response,
        ):
            with self.assertRaises(UserError):
                provider._paypal_retrieve("https://url", "")

    def test_create_empty_paypal_statements(self):
        """Test creating empty PayPal statements
        ('Allow empty statements' field is checked).
        """
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response_1 = json.loads(f"""{{
    "transaction_details": [],
    "account_number": "1234567890",
    "start_date": "{self.now_isoformat}",
    "end_date": "{self.now_isoformat}",
    "last_refreshed_datetime": "{self.now_isoformat}",
    "page": 1,
    "total_items": 0,
    "total_pages": 0
}}""")
        mocked_response_2 = json.loads(f"""{{
    "balances": [
        {{
            "currency": "EUR",
            "primary": true,
            "total_balance": {{
                "currency_code": "EUR",
                "value": "0.75"
            }},
            "available_balance": {{
                "currency_code": "EUR",
                "value": "0.75"
            }},
            "withheld_balance": {{
                "currency_code": "EUR",
                "value": "0.00"
            }}
        }}
    ],
    "account_id": "1234567890",
    "as_of_time": "{self.now_isoformat}",
    "last_refresh_time": "{self.now_isoformat}"
}}""")
        with (
            mock.patch(
                _provider_class + "._paypal_retrieve",
                side_effect=[mocked_response_1, mocked_response_2],
            ),
            self.mock_token(),
        ):
            data = provider._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertEqual(data, ([], {"balance_start": 0.75, "balance_end_real": 0.75}))

    def test_ancient_pull(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads(f"""{{
    "transaction_details": [],
    "account_number": "1234567890",
    "start_date": "{self.now_isoformat}",
    "end_date": "{self.now_isoformat}",
    "last_refreshed_datetime": "{self.now_isoformat}",
    "page": 1,
    "total_items": 0,
    "total_pages": 0
}}""")
        with (
            mock.patch(
                _provider_class + "._paypal_retrieve",
                return_value=mocked_response,
            ),
            self.mock_token(),
        ):
            with self.assertRaisesRegex(
                UserError,
                "PayPal allows retrieving transactions only up to 3 years in "
                "the past. Please import older transactions manually.",
            ):
                provider._obtain_statement_data(
                    self.now - relativedelta(years=5),
                    self.now,
                )

    def test_pull(self):
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads(f"""{{
    "transaction_details": [{{
        "transaction_info": {{
            "paypal_account_id": "1234567890",
            "transaction_id": "1234567890",
            "transaction_event_code": "T1234",
            "transaction_initiation_date": "{self.yesterday_isoformat}",
            "transaction_updated_date": "{self.yesterday_isoformat}",
            "transaction_amount": {{
                "currency_code": "USD",
                "value": "1000.00"
            }},
            "fee_amount": {{
                "currency_code": "USD",
                "value": "-100.00"
            }},
            "transaction_status": "S",
            "transaction_subject": "Payment for Invoice(s) 1",
            "ending_balance": {{
                "currency_code": "USD",
                "value": "900.00"
            }},
            "available_balance": {{
                "currency_code": "USD",
                "value": "900.00"
            }},
            "invoice_id": "1"
        }},
        "payer_info": {{
            "account_id": "1234567890",
            "email_address": "partner@example.com",
            "address_status": "Y",
            "payer_status": "N",
            "payer_name": {{
                "alternate_full_name": "Acme, Inc."
            }},
            "country_code": "US"
        }},
        "shipping_info": {{}},
        "cart_info": {{}},
        "store_info": {{}},
        "auction_info": {{}},
        "incentive_info": {{}}
    }}, {{
        "transaction_info": {{
            "paypal_account_id": "1234567890",
            "transaction_id": "1234567891",
            "transaction_event_code": "T1234",
            "transaction_initiation_date": "{self.today_isoformat}",
            "transaction_updated_date": "{self.today_isoformat}",
            "transaction_amount": {{
                "currency_code": "USD",
                "value": "1000.00"
            }},
            "fee_amount": {{
                "currency_code": "USD",
                "value": "-100.00"
            }},
            "transaction_status": "S",
            "transaction_subject": "Payment for Invoice(s) 1",
            "ending_balance": {{
                "currency_code": "USD",
                "value": "900.00"
            }},
            "available_balance": {{
                "currency_code": "USD",
                "value": "900.00"
            }},
            "invoice_id": "1"
        }},
        "payer_info": {{
            "account_id": "1234567890",
            "email_address": "partner@example.com",
            "address_status": "Y",
            "payer_status": "N",
            "payer_name": {{
                "alternate_full_name": "Acme, Inc."
            }},
            "country_code": "US"
        }},
        "shipping_info": {{}},
        "cart_info": {{}},
        "store_info": {{}},
        "auction_info": {{}},
        "incentive_info": {{}}
    }}],
    "account_number": "1234567890",
    "start_date": "{self.yesterday_isoformat}",
    "end_date": "{self.today_isoformat}",
    "last_refreshed_datetime": "{self.now_isoformat}",
    "page": 1,
    "total_items": 1,
    "total_pages": 1
}}""")
        with (
            mock.patch(
                _provider_class + "._paypal_retrieve",
                return_value=mocked_response,
            ),
            self.mock_token(),
        ):
            data = provider._obtain_statement_data(
                self.yesterday,
                self.today,
            )

        self.assertEqual(len(data[0]), 2)
        del data[0][0]["raw_data"]
        self.assertEqual(
            data[0][0],
            {
                "date": self.yesterday,
                "amount": "1000.00",
                "ref": "Invoice 1",
                "payment_ref": "1234567890: Payment for Invoice(s) 1",
                "partner_name": "Acme, Inc.",
                "unique_import_id": f"1234567890-{self.yesterday_timestamp}",
            },
        )
        self.assertEqual(
            data[0][1],
            {
                "date": self.yesterday,
                "amount": "-100.00",
                "ref": "Fee for Invoice 1",
                "payment_ref": "Transaction fee for 1234567890: Payment for Invoice(s)"
                " 1",
                "partner_name": "PayPal",
                "unique_import_id": f"1234567890-{self.yesterday_timestamp}-FEE",
            },
        )
        self.assertEqual(data[1], {"balance_start": 0.0, "balance_end_real": 900.0})

    def test_transaction_parse_1(self):
        lines = self.paypal_parse_transaction(f"""{{
    "transaction_info": {{
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "{self.today_isoformat}",
        "transaction_updated_date": "{self.today_isoformat}",
        "transaction_amount": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "fee_amount": {{
            "currency_code": "USD",
            "value": "0.00"
        }},
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "available_balance": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "invoice_id": "1"
    }},
    "payer_info": {{
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {{
            "alternate_full_name": "Acme, Inc."
        }},
        "country_code": "US"
    }},
    "shipping_info": {{}},
    "cart_info": {{}},
    "store_info": {{}},
    "auction_info": {{}},
    "incentive_info": {{}}
}}""")
        self.assertEqual(len(lines), 1)
        del lines[0]["raw_data"]
        self.assertEqual(
            lines[0],
            {
                "date": self.today,
                "amount": "1000.00",
                "ref": "Invoice 1",
                "payment_ref": "1234567890: Payment for Invoice(s) 1",
                "partner_name": "Acme, Inc.",
                "unique_import_id": f"1234567890-{self.today_timestamp}",
            },
        )

    def test_transaction_parse_2(self):
        lines = self.paypal_parse_transaction(f"""{{
    "transaction_info": {{
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "{self.today_isoformat}",
        "transaction_updated_date": "{self.today_isoformat}",
        "transaction_amount": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "fee_amount": {{
            "currency_code": "USD",
            "value": "0.00"
        }},
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "available_balance": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "invoice_id": "1"
    }},
    "payer_info": {{
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {{
            "alternate_full_name": "Acme, Inc."
        }},
        "country_code": "US"
    }},
    "shipping_info": {{}},
    "cart_info": {{}},
    "store_info": {{}},
    "auction_info": {{}},
    "incentive_info": {{}}
}}""")

        self.assertEqual(len(lines), 1)
        del lines[0]["raw_data"]
        self.assertEqual(
            lines[0],
            {
                "date": self.today,
                "amount": "1000.00",
                "ref": "Invoice 1",
                "payment_ref": "1234567890: Payment for Invoice(s) 1",
                "partner_name": "Acme, Inc.",
                "unique_import_id": f"1234567890-{self.today_timestamp}",
            },
        )

    def test_transaction_parse_3(self):
        lines = self.paypal_parse_transaction(f"""{{
    "transaction_info": {{
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "{self.today_isoformat}",
        "transaction_updated_date": "{self.today_isoformat}",
        "transaction_amount": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "fee_amount": {{
            "currency_code": "USD",
            "value": "-100.00"
        }},
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {{
            "currency_code": "USD",
            "value": "900.00"
        }},
        "available_balance": {{
            "currency_code": "USD",
            "value": "900.00"
        }},
        "invoice_id": "1"
    }},
    "payer_info": {{
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {{
            "alternate_full_name": "Acme, Inc."
        }},
        "country_code": "US"
    }},
    "shipping_info": {{}},
    "cart_info": {{}},
    "store_info": {{}},
    "auction_info": {{}},
    "incentive_info": {{}}
}}""")
        self.assertEqual(len(lines), 2)
        del lines[0]["raw_data"]
        self.assertEqual(
            lines[0],
            {
                "date": self.today,
                "amount": "1000.00",
                "ref": "Invoice 1",
                "payment_ref": "1234567890: Payment for Invoice(s) 1",
                "partner_name": "Acme, Inc.",
                "unique_import_id": f"1234567890-{self.today_timestamp}",
            },
        )
        self.assertEqual(
            lines[1],
            {
                "date": self.today,
                "amount": "-100.00",
                "ref": "Fee for Invoice 1",
                "payment_ref": "Transaction fee for 1234567890: Payment for Invoice(s)"
                " 1",
                "partner_name": "PayPal",
                "unique_import_id": f"1234567890-{self.today_timestamp}-FEE",
            },
        )

    def test_transaction_parse_4(self):
        lines = self.paypal_parse_transaction(f"""{{
    "transaction_info": {{
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "{self.today_isoformat}",
        "transaction_updated_date": "{self.today_isoformat}",
        "transaction_amount": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "available_balance": {{
            "currency_code": "USD",
            "value": "1000.00"
        }},
        "invoice_id": "1"
    }},
    "payer_info": {{
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {{
            "alternate_full_name": "Acme, Inc."
        }},
        "country_code": "US"
    }},
    "shipping_info": {{}},
    "cart_info": {{}},
    "store_info": {{}},
    "auction_info": {{}},
    "incentive_info": {{}}
}}""")
        self.assertEqual(len(lines), 1)
        del lines[0]["raw_data"]
        self.assertEqual(
            lines[0],
            {
                "date": self.today,
                "amount": "1000.00",
                "ref": "Invoice 1",
                "payment_ref": "1234567890: Payment for Invoice(s) 1",
                "partner_name": "Acme, Inc.",
                "unique_import_id": f"1234567890-{self.today_timestamp}",
            },
        )

    def test_retrieve_invalid_json_response(self):
        """Cover new logic: if PayPal returns non-JSON body, raise UserError."""
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )
        provider = journal.online_bank_statement_provider_id
        mocked_response = UrlopenRetValMock("<html>not a json</html>", throw=False)
        with mock.patch(
            _provider_class + "._paypal_urlopen",
            return_value=mocked_response,
        ):
            with self.assertRaisesRegex(
                UserError, "Invalid JSON response from PayPal API"
            ):
                provider._paypal_retrieve("https://url", "--TOKEN--")

    def test_get_transactions_missing_transaction_details(self):
        """
        Response without `transaction_details` must
        not crash and should return empty list.
        """
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )
        provider = journal.online_bank_statement_provider_id
        # PayPal-like error payload without `transaction_details`
        mocked_payload = {
            "name": "INVALID_REQUEST",
            "message": "Request is not well-formed, syntactically "
            "incorrect, or violates schema.",
            # so that the page cycle ends correctly
            "total_pages": 0,
        }
        since = self.now - relativedelta(hours=1)
        until = self.now
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_payload,
        ):
            tx = provider._paypal_get_transactions("--TOKEN--", "EUR", since, until)
        self.assertEqual(tx, [])

    def test_paypal_format_datetime(self):
        """
        Ensure PayPal datetime formatter drops
        microseconds and uses UTC Z format.
        """
        journal = self.AccountJournal.create(
            {
                "name": "Bank",
                "type": "bank",
                "code": "BANK",
                "currency_id": self.currency_eur.id,
                "bank_statements_source": "online",
                "online_bank_statement_provider": "paypal",
            }
        )
        provider = journal.online_bank_statement_provider_id
        # None -> None
        self.assertIsNone(provider._paypal_format_datetime(None))
        # Drops microseconds + Z format
        dt = datetime(2026, 1, 15, 11, 28, 27, 749445)  # naive UTC
        self.assertEqual(
            provider._paypal_format_datetime(dt),
            "2026-01-15T11:28:27Z",
        )

    def _odoo_obtain_lines(self, odoo_payments=None, line_values=None):
        with (
            patch(f"{ODOO_MODULE}._paypal_get_token", return_value="TOKEN"),
            patch(
                f"{ODOO_MODULE}._paypal_get_transactions",
                return_value=self.odoo_transactions,
            ),
            patch(
                f"{ODOO_MODULE}._paypal_get_transaction",
                return_value=self.odoo_transactions[0],
            ),
            patch(
                f"{ODOO_MODULE}._paypal_get_odoo_payments",
                return_value=odoo_payments or {},
            ) as get_odoo_payments,
            patch(
                f"{ODOO_MODULE}._paypal_odoo_payment_line_values",
                side_effect=lambda payment: line_values[payment],
            ),
        ):
            lines, __ = self.odoo_provider._obtain_statement_data(
                ODOO_DAY, ODOO_DAY + timedelta(days=1)
            )
        return {line["unique_import_id"]: line for line in lines}, get_odoo_payments

    def test_payment_keys(self):
        self.assertEqual(_paypal_payment_keys(self.odoo_transactions[0]), {"CAPTURE1"})
        self.assertEqual(
            _paypal_payment_keys(self.odoo_transactions[1]), {"CAPTURE2", "ORDER2"}
        )
        # A refund refers to the payment it refunds: not a key of the refund
        refund = _odoo_transaction("REFUND1")
        refund["transaction_info"].update(
            paypal_reference_id="CAPTURE1", paypal_reference_id_type="TXN"
        )
        self.assertEqual(_paypal_payment_keys(refund), {"REFUND1"})

    def test_payments_recorded_by_odoo(self):
        lines, __ = self._odoo_obtain_lines(
            {"CAPTURE1": "posted on the journal", "ORDER2": "to reconcile"},
            {
                "posted on the journal": None,
                "to reconcile": {"partner_id": self.odoo_partner.id},
            },
        )
        timestamp = int((ODOO_DAY + timedelta(hours=10)).timestamp())
        # Already posted on the journal: only its fee is imported
        self.assertNotIn(f"CAPTURE1-{timestamp}", lines)
        self.assertIn(f"CAPTURE1-{timestamp}-FEE", lines)
        # Recorded elsewhere (found by its order): imported with the partner
        self.assertEqual(
            lines[f"CAPTURE2-{timestamp}"]["partner_id"], self.odoo_partner.id
        )
        self.assertNotIn("partner_id", lines[f"CAPTURE2-{timestamp}-FEE"])
        # Not recorded by Odoo: imported as usual
        self.assertNotIn("partner_id", lines[f"CAPTURE3-{timestamp}"])

    def test_option_disabled(self):
        self.odoo_provider.paypal_skip_website_payments = False
        lines, get_odoo_payments = self._odoo_obtain_lines()
        get_odoo_payments.assert_not_called()
        self.assertEqual(len(lines), 6)

    def test_order_captures(self):
        order = {
            "id": "ORDER3",
            "purchase_units": [
                {"payments": {"captures": [{"id": "CAPTURE3"}, {"id": "CAPTURE4"}]}},
                {"reference_id": "without payments"},
            ],
        }
        with patch(f"{ODOO_MODULE}._paypal_retrieve", return_value=order) as retrieve:
            captures = self.odoo_provider._paypal_get_order_captures("TOKEN", "ORDER3")
        self.assertEqual(captures, ["CAPTURE3", "CAPTURE4"])
        retrieve.assert_called_once_with(
            "https://api.paypal.com/v2/checkout/orders/ORDER3", "TOKEN"
        )
        # Not an order (for instance a capture): nothing, without error
        with patch(
            f"{ODOO_MODULE}._paypal_retrieve",
            side_effect=UserError("RESOURCE_NOT_FOUND: not found"),
        ):
            self.assertEqual(
                self.odoo_provider._paypal_get_order_captures("TOKEN", "CAPTURE1"), []
            )

    def test_odoo_payments_search(self):
        """With the PayPal payment provider, find the done transactions"""
        if "payment.transaction" not in self.env:
            self.skipTest("The Payment module is not installed")
        paypal = self.env["payment.provider"].search([("code", "=", "paypal")], limit=1)
        if not paypal:
            self.skipTest("The PayPal payment provider is not installed")
        method = (
            self.env["payment.method"]
            .with_context(active_test=False)
            .search([("code", "=", "paypal")], limit=1)
        )
        values = {
            "provider_id": paypal.id,
            "payment_method_id": method.id,
            "amount": 10.0,
            "currency_id": self.env.ref("base.USD").id,
            "partner_id": self.odoo_partner.id,
        }
        done, __, by_webhook, earlier = self.env["payment.transaction"].create(
            [
                dict(values, reference="T1", provider_reference="ORDER2", state="done"),
                dict(values, reference="T2", provider_reference="CAPTURE3"),
                # The webhook stored the order: its capture is read from PayPal
                dict(values, reference="T3", provider_reference="ORDER3", state="done"),
                dict(values, reference="T4", provider_reference="ORDER4", state="done"),
            ]
        )
        by_webhook.last_state_change = ODOO_DAY + timedelta(hours=11)
        # Done long before the transactions: its order is not read
        earlier.last_state_change = ODOO_DAY - timedelta(days=5)
        orders = {"ORDER3": ["CAPTURE3"], "ORDER4": ["CAPTURE1"]}
        with patch(
            f"{ODOO_MODULE}._paypal_get_order_captures",
            side_effect=lambda token, order_id: orders.get(order_id, []),
        ) as get_order_captures:
            odoo_payments = self.odoo_provider._paypal_get_odoo_payments(
                "TOKEN", self.odoo_transactions
            )
        self.assertEqual(odoo_payments, {"ORDER2": done, "CAPTURE3": by_webhook})
        get_order_captures.assert_called_once_with("TOKEN", "ORDER3")
        # Without a payment posted on the journal, the line gets the partner
        self.assertEqual(
            self.odoo_provider._paypal_odoo_payment_line_values(done),
            {"partner_id": self.odoo_partner.id},
        )
        if "payment_id" not in done._fields:
            return
        # Payment posted directly on the account of the journal: line skipped
        method_line = self.odoo_journal.inbound_payment_method_line_ids[:1]
        method_line.payment_account_id = self.odoo_journal.default_account_id
        payment = self.env["account.payment"].create(
            {
                "payment_type": "inbound",
                "partner_type": "customer",
                "partner_id": self.odoo_partner.id,
                "amount": 10.0,
                "journal_id": self.odoo_journal.id,
                "payment_method_line_id": method_line.id,
            }
        )
        payment.action_post()
        done.payment_id = payment
        self.assertIsNone(self.odoo_provider._paypal_odoo_payment_line_values(done))
