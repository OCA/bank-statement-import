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
from odoo.tools import mute_logger

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


CURRENCY_MODULE = (
    "odoo.addons.account_statement_import_online_paypal.models"
    ".online_bank_statement_provider_paypal.OnlineBankStatementProviderPayPal"
)


CURRENCY_DAY = datetime.combine(datetime.now().date(), datetime.min.time()) - timedelta(
    days=1
)


CONVERTED_DAY = datetime.combine(
    datetime.now().date(), datetime.min.time()
) - timedelta(days=1)


CONVERTED_DATE = CONVERTED_DAY + timedelta(hours=10)


CONVERTED_TIMESTAMP = int(CONVERTED_DATE.timestamp())


CONVERTED_MODULE = (
    "odoo.addons.account_statement_import_online_paypal.models"
    ".online_bank_statement_provider_paypal.OnlineBankStatementProviderPayPal"
)


def _converted_transaction(transaction_id, event_code, currency, amount, **info):
    values = {
        "transaction_id": transaction_id,
        "transaction_event_code": event_code,
        "transaction_updated_date": CONVERTED_DATE,
        "transaction_amount": {"currency_code": currency, "value": amount},
        "available_balance": {"currency_code": currency, "value": "100.00"},
    }
    values.update(info)
    return {
        "transaction_info": values,
        "payer_info": {"address_status": "N", "payer_name": {}},
        "cart_info": {},
    }


def _converted_conversion(transaction_id, currency, amount, payment_id):
    return _converted_transaction(
        transaction_id,
        "T0200",
        currency,
        amount,
        paypal_reference_id=payment_id,
        paypal_reference_id_type="TXN",
        instrument_type="PayPal",
    )


def _converted_payment(transaction_id, currency, amount, fee):
    payment = _converted_transaction(
        transaction_id,
        "T0006",
        currency,
        amount,
        fee_amount={"currency_code": currency, "value": fee},
        transaction_subject="Donation",
        paypal_account_id="PAYER1",
        instrument_type="Credit Card",
    )
    payment["payer_info"] = {
        "account_id": "PAYER1",
        "email_address": "payer@example.com",
        "payer_name": {"alternate_full_name": "John Doe"},
    }
    return payment


class TestAccountBankAccountStatementImportOnlinePayPal(common.TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency_eur = cls.env.ref("base.EUR")
        cls.currency_usd = cls.env.ref("base.USD")
        cls.currency_usd.active = True
        cls.currency_journal = cls.env["account.journal"].create(
            {
                "name": "PayPal EUR",
                "type": "bank",
                "code": "PCUR",
                "bank_statements_source": "online",
                "currency_id": cls.currency_eur.id,
            }
        )
        cls.currency_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "paypal",
                "username": "client_id",
                "password": "secret",
                "journal_id": cls.currency_journal.id,
            }
        )
        cls.converted_usd = cls.env.ref("base.USD")
        cls.converted_eur = cls.env.ref("base.EUR")
        (cls.converted_usd | cls.converted_eur).active = True
        cls.converted_journal = cls.env["account.journal"].create(
            {
                "name": "PayPal",
                "type": "bank",
                "code": "PCONV",
                "bank_statements_source": "online",
                "currency_id": cls.converted_eur.id,
            }
        )
        cls.converted_provider = cls.env["online.bank.statement.provider"].create(
            {
                "service": "paypal",
                "username": "client_id",
                "password": "secret",
                "journal_id": cls.converted_journal.id,
            }
        )

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
        # The requests of the balances in other currencies are tested apart
        self.mock_warn_other_currencies = lambda: mock.patch(
            _provider_class + "._paypal_warn_other_currencies",
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
            self.mock_warn_other_currencies(),
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
            self.mock_warn_other_currencies(),
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

    def _currency_warn(self, before, after):
        with patch(
            f"{CURRENCY_MODULE}._paypal_get_balances", side_effect=[before, after]
        ):
            self.currency_provider._paypal_warn_other_currencies(
                "TOKEN", "EUR", CURRENCY_DAY, CURRENCY_DAY + timedelta(days=1)
            )

    def _currency_messages(self):
        return self.currency_provider.message_ids.filtered(
            lambda message: "were not imported" in (message.body or "")
        )

    def test_get_balances(self):
        response = {
            "balances": [
                {
                    "currency": "EUR",
                    "primary": True,
                    "available_balance": {"currency_code": "EUR", "value": "10.50"},
                },
                {
                    "currency": "USD",
                    "available_balance": {"currency_code": "USD", "value": "3.00"},
                },
                {"currency": "GBP"},
            ]
        }
        with patch(
            f"{CURRENCY_MODULE}._paypal_retrieve", return_value=response
        ) as retrieve:
            balances = self.currency_provider._paypal_get_balances(
                "TOKEN", CURRENCY_DAY
            )
        self.assertEqual(balances, {"EUR": Decimal("10.50"), "USD": Decimal("3.00")})
        self.assertIn("/v1/reporting/balances?as_of_time=", retrieve.call_args[0][0])

    @mute_logger(
        "odoo.addons.account_statement_import_online_paypal.models."
        "online_bank_statement_provider_paypal"
    )
    def test_other_currency_changed(self):
        self._currency_warn(
            {"EUR": Decimal(10), "USD": Decimal(0)},
            {"EUR": Decimal(20), "USD": Decimal(5)},
        )
        self.assertEqual(len(self._currency_messages()), 1)
        self.assertIn("USD", self._currency_messages().body)
        # Once, not at each pull
        self._currency_warn({"USD": Decimal(5)}, {"USD": Decimal(8)})
        self.assertEqual(len(self._currency_messages()), 1)

    def test_other_currency_unchanged(self):
        self._currency_warn(
            {"EUR": Decimal(10), "USD": Decimal(5)}, {"USD": Decimal(5)}
        )
        self.assertFalse(self._currency_messages())

    def test_other_currency_imported(self):
        """No warning when another provider imports that currency"""
        journal = self.env["account.journal"].create(
            {
                "name": "PayPal USD",
                "type": "bank",
                "code": "PPUSD",
                "bank_statements_source": "online",
                "currency_id": self.currency_usd.id,
            }
        )
        self.env["online.bank.statement.provider"].create(
            {
                "service": "paypal",
                "username": "client_id",
                "password": "secret",
                "journal_id": journal.id,
            }
        )
        self._currency_warn({"USD": Decimal(0)}, {"USD": Decimal(5)})
        self.assertFalse(self._currency_messages())

    @mute_logger(
        "odoo.addons.account_statement_import_online_paypal.models."
        "online_bank_statement_provider_paypal"
    )
    def test_balances_not_available(self):
        """An error on the balances does not stop the pull"""
        with patch(
            f"{CURRENCY_MODULE}._paypal_get_balances",
            side_effect=UserError("No balances"),
        ):
            self.currency_provider._paypal_warn_other_currencies(
                "TOKEN", "EUR", CURRENCY_DAY, CURRENCY_DAY + timedelta(days=1)
            )
        self.assertFalse(self._currency_messages())

    def test_pull_warns(self):
        with (
            patch(f"{CURRENCY_MODULE}._paypal_get_token", return_value="TOKEN"),
            patch(f"{CURRENCY_MODULE}._paypal_get_transactions", return_value=[]),
            patch(f"{CURRENCY_MODULE}._paypal_get_balance", return_value=Decimal(0)),
            patch(f"{CURRENCY_MODULE}._paypal_warn_other_currencies") as warn,
        ):
            self.currency_provider._obtain_statement_data(
                CURRENCY_DAY, CURRENCY_DAY + timedelta(days=1)
            )
        warn.assert_called_once_with(
            "TOKEN", "EUR", CURRENCY_DAY, CURRENCY_DAY + timedelta(days=1)
        )

    def _converted_obtain_lines(self, journal_transactions, all_transactions):
        def get_transactions(token, currency, since, until):
            return journal_transactions if currency else all_transactions

        with (
            patch(f"{CONVERTED_MODULE}._paypal_get_token", return_value="TOKEN"),
            patch(
                f"{CONVERTED_MODULE}._paypal_get_transactions",
                side_effect=get_transactions,
            ) as get_transactions_mock,
            patch(
                f"{CONVERTED_MODULE}._paypal_get_transaction",
                return_value=journal_transactions[0],
            ),
            # The balances in other currencies are tested apart
            patch(f"{CONVERTED_MODULE}._paypal_warn_other_currencies"),
        ):
            lines, __ = self.converted_provider._obtain_statement_data(
                CONVERTED_DAY, CONVERTED_DAY + timedelta(days=1)
            )
        currencies = [call.args[1] for call in get_transactions_mock.call_args_list]
        return {line["unique_import_id"]: line for line in lines}, currencies

    def test_converted_payment(self):
        """The conversion of a payment in USD gets the payer and the USD amount"""
        payment = _converted_payment("PAYMENT1", "USD", "25.00", "-0.60")
        journal_transactions = [
            _converted_conversion("CONV1-EUR", "EUR", "21.13", "PAYMENT1")
        ]
        all_transactions = [
            payment,
            _converted_conversion("CONV1-USD", "USD", "-24.40", "PAYMENT1"),
            _converted_conversion("CONV1-EUR", "EUR", "21.13", "PAYMENT1"),
        ]
        lines, currencies = self._converted_obtain_lines(
            journal_transactions, all_transactions
        )
        self.assertEqual(currencies, ["EUR", None])
        line = lines[f"CONV1-EUR-{CONVERTED_TIMESTAMP}"]
        self.assertEqual(line["amount"], "21.13")
        self.assertEqual(line["partner_name"], "John Doe")
        self.assertEqual(line["ref"], "Donation")
        self.assertTrue(line["payment_ref"].startswith("CONV1-EUR: Donation"))
        self.assertEqual(line["foreign_currency_id"], self.converted_usd.id)
        # Net of the fee, taken in USD before the conversion
        self.assertEqual(line["amount_currency"], "24.40")
        info = journal_transactions[0]["transaction_info"]
        self.assertEqual(info["paypal_account_id"], "PAYER1")
        self.assertEqual(info["instrument_type"], "Credit Card")
        self.assertEqual(
            journal_transactions[0]["payer_info"]["email_address"],
            "payer@example.com",
        )
        self.assertIs(journal_transactions[0]["converted_transaction"], payment)
        # The conversion has no fee of its own
        self.assertEqual(len(lines), 1)

    def test_converted_refund(self):
        """A refund in USD converted from EUR gets a negative USD amount"""
        refund = _converted_payment("REFUND1", "USD", "-10.00", "0.00")
        journal_transactions = [
            _converted_conversion("CONV2-EUR", "EUR", "-8.66", "REFUND1")
        ]
        lines, __ = self._converted_obtain_lines(
            journal_transactions, [refund] + journal_transactions
        )
        line = lines[f"CONV2-EUR-{CONVERTED_TIMESTAMP}"]
        self.assertEqual(line["foreign_currency_id"], self.converted_usd.id)
        self.assertEqual(line["amount_currency"], "-10.00")

    def test_without_conversions(self):
        """Without conversions, the transactions of other currencies are not read"""
        journal_transactions = [_converted_payment("PAYMENT2", "EUR", "10.00", "-0.50")]
        lines, currencies = self._converted_obtain_lines(journal_transactions, [])
        self.assertEqual(currencies, ["EUR"])
        line = lines[f"PAYMENT2-{CONVERTED_TIMESTAMP}"]
        self.assertNotIn("foreign_currency_id", line)
        self.assertEqual(line["partner_name"], "John Doe")

    def test_payment_not_found(self):
        """A conversion whose payment is not found is imported as before"""
        journal_transactions = [
            _converted_conversion("CONV3-EUR", "EUR", "5.00", "MISSING")
        ]
        lines, __ = self._converted_obtain_lines(
            journal_transactions, journal_transactions
        )
        line = lines[f"CONV3-EUR-{CONVERTED_TIMESTAMP}"]
        self.assertNotIn("foreign_currency_id", line)
        self.assertNotIn("partner_name", line)
        self.assertEqual(line["payment_ref"], "CONV3-EUR")

    def test_statement_line_in_foreign_currency(self):
        """The line of the conversion is created with its USD amount"""
        journal_transactions = [
            _converted_conversion("CONV4-EUR", "EUR", "21.13", "PAYMENT4")
        ]
        all_transactions = [
            _converted_payment("PAYMENT4", "USD", "25.00", "-0.60")
        ] + journal_transactions
        lines, __ = self._converted_obtain_lines(journal_transactions, all_transactions)
        values = dict(lines[f"CONV4-EUR-{CONVERTED_TIMESTAMP}"])
        values.pop("raw_data")
        line = self.env["account.bank.statement.line"].create(
            dict(values, journal_id=self.converted_journal.id)
        )
        self.assertEqual(line.foreign_currency_id, self.converted_usd)
        self.assertAlmostEqual(line.amount_currency, 24.40)
        self.assertAlmostEqual(line.amount, 21.13)
