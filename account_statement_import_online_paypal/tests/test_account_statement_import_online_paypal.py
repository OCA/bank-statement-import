# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2021-2022 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

import json
from datetime import datetime
from decimal import Decimal
from unittest import mock
from urllib.error import HTTPError

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

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


class TestAccountBankAccountStatementImportOnlinePayPal(common.TransactionCase):
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
        token = None
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
            with self.assertRaises(Exception):
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
            with self.assertRaises(Exception):
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
            with self.assertRaises(Exception):
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
            """{
    "balances": [
        {
            "currency": "EUR",
            "primary": true,
            "total_balance": {
                "currency_code": "EUR",
                "value": "0.75"
            },
            "available_balance": {
                "currency_code": "EUR",
                "value": "0.75"
            },
            "withheld_balance": {
                "currency_code": "EUR",
                "value": "0.00"
            }
        }
    ],
    "account_id": "1234567890",
    "as_of_time": "%s",
    "last_refresh_time": "%s"
}"""
            % (
                self.now_isoformat,
                self.now_isoformat,
            )
        )
        with mock.patch(
            _provider_class + "._paypal_urlopen",
            side_effect=[mocked_response_1, mocked_response_2],
        ), self.mock_token():
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

    def test_empty_pull(self):
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
        mocked_response_1 = json.loads(
            """{
    "transaction_details": [],
    "account_number": "1234567890",
    "start_date": "%s",
    "end_date": "%s",
    "last_refreshed_datetime": "%s",
    "page": 1,
    "total_items": 0,
    "total_pages": 0
}"""
            % (
                self.now_isoformat,
                self.now_isoformat,
                self.now_isoformat,
            ),
            parse_float=Decimal,
        )
        mocked_response_2 = json.loads(
            """{
    "balances": [
        {
            "currency": "EUR",
            "primary": true,
            "total_balance": {
                "currency_code": "EUR",
                "value": "0.75"
            },
            "available_balance": {
                "currency_code": "EUR",
                "value": "0.75"
            },
            "withheld_balance": {
                "currency_code": "EUR",
                "value": "0.00"
            }
        }
    ],
    "account_id": "1234567890",
    "as_of_time": "%s",
    "last_refresh_time": "%s"
}"""
            % (
                self.now_isoformat,
                self.now_isoformat,
            ),
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            side_effect=[mocked_response_1, mocked_response_2],
        ), self.mock_token():
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
        mocked_response = json.loads(
            """{
    "transaction_details": [],
    "account_number": "1234567890",
    "start_date": "%s",
    "end_date": "%s",
    "last_refreshed_datetime": "%s",
    "page": 1,
    "total_items": 0,
    "total_pages": 0
}"""
            % (
                self.now_isoformat,
                self.now_isoformat,
                self.now_isoformat,
            ),
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_response,
        ), self.mock_token():
            with self.assertRaises(Exception):
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
        mocked_response = json.loads(
            """{
    "transaction_details": [{
        "transaction_info": {
            "paypal_account_id": "1234567890",
            "transaction_id": "1234567890",
            "transaction_event_code": "T1234",
            "transaction_initiation_date": "%s",
            "transaction_updated_date": "%s",
            "transaction_amount": {
                "currency_code": "USD",
                "value": "1000.00"
            },
            "fee_amount": {
                "currency_code": "USD",
                "value": "-100.00"
            },
            "transaction_status": "S",
            "transaction_subject": "Payment for Invoice(s) 1",
            "ending_balance": {
                "currency_code": "USD",
                "value": "900.00"
            },
            "available_balance": {
                "currency_code": "USD",
                "value": "900.00"
            },
            "invoice_id": "1"
        },
        "payer_info": {
            "account_id": "1234567890",
            "email_address": "partner@example.com",
            "address_status": "Y",
            "payer_status": "N",
            "payer_name": {
                "alternate_full_name": "Acme, Inc."
            },
            "country_code": "US"
        },
        "shipping_info": {},
        "cart_info": {},
        "store_info": {},
        "auction_info": {},
        "incentive_info": {}
    }, {
        "transaction_info": {
            "paypal_account_id": "1234567890",
            "transaction_id": "1234567891",
            "transaction_event_code": "T1234",
            "transaction_initiation_date": "%s",
            "transaction_updated_date": "%s",
            "transaction_amount": {
                "currency_code": "USD",
                "value": "1000.00"
            },
            "fee_amount": {
                "currency_code": "USD",
                "value": "-100.00"
            },
            "transaction_status": "S",
            "transaction_subject": "Payment for Invoice(s) 1",
            "ending_balance": {
                "currency_code": "USD",
                "value": "900.00"
            },
            "available_balance": {
                "currency_code": "USD",
                "value": "900.00"
            },
            "invoice_id": "1"
        },
        "payer_info": {
            "account_id": "1234567890",
            "email_address": "partner@example.com",
            "address_status": "Y",
            "payer_status": "N",
            "payer_name": {
                "alternate_full_name": "Acme, Inc."
            },
            "country_code": "US"
        },
        "shipping_info": {},
        "cart_info": {},
        "store_info": {},
        "auction_info": {},
        "incentive_info": {}
    }],
    "account_number": "1234567890",
    "start_date": "%s",
    "end_date": "%s",
    "last_refreshed_datetime": "%s",
    "page": 1,
    "total_items": 1,
    "total_pages": 1
}"""
            % (
                self.yesterday_isoformat,
                self.yesterday_isoformat,
                self.today_isoformat,
                self.today_isoformat,
                self.yesterday_isoformat,
                self.today_isoformat,
                self.now_isoformat,
            ),
            parse_float=Decimal,
        )
        with mock.patch(
            _provider_class + "._paypal_retrieve",
            return_value=mocked_response,
        ), self.mock_token():
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
                "unique_import_id": "1234567890-%s" % (self.yesterday_timestamp,),
            },
        )
        self.assertEqual(
            data[0][1],
            {
                "date": self.yesterday,
                "amount": "-100.00",
                "ref": "Fee for Invoice 1",
                "payment_ref": "Transaction fee for 1234567890: Payment for Invoice(s) 1",
                "partner_name": "PayPal",
                "unique_import_id": "1234567890-%s-FEE" % (self.yesterday_timestamp,),
            },
        )
        self.assertEqual(data[1], {"balance_start": 0.0, "balance_end_real": 900.0})

    def test_transaction_parse_1(self):
        lines = self.paypal_parse_transaction(
            """{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "%s",
        "transaction_updated_date": "%s",
        "transaction_amount": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "fee_amount": {
            "currency_code": "USD",
            "value": "0.00"
        },
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "available_balance": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "invoice_id": "1"
    },
    "payer_info": {
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {
            "alternate_full_name": "Acme, Inc."
        },
        "country_code": "US"
    },
    "shipping_info": {},
    "cart_info": {},
    "store_info": {},
    "auction_info": {},
    "incentive_info": {}
}"""
            % (
                self.today_isoformat,
                self.today_isoformat,
            )
        )
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
                "unique_import_id": "1234567890-%s" % (self.today_timestamp,),
            },
        )

    def test_transaction_parse_2(self):
        lines = self.paypal_parse_transaction(
            """{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "%s",
        "transaction_updated_date": "%s",
        "transaction_amount": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "fee_amount": {
            "currency_code": "USD",
            "value": "0.00"
        },
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "available_balance": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "invoice_id": "1"
    },
    "payer_info": {
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {
            "alternate_full_name": "Acme, Inc."
        },
        "country_code": "US"
    },
    "shipping_info": {},
    "cart_info": {},
    "store_info": {},
    "auction_info": {},
    "incentive_info": {}
}"""
            % (
                self.today_isoformat,
                self.today_isoformat,
            )
        )
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
                "unique_import_id": "1234567890-%s" % (self.today_timestamp,),
            },
        )

    def test_transaction_parse_3(self):
        lines = self.paypal_parse_transaction(
            """{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "%s",
        "transaction_updated_date": "%s",
        "transaction_amount": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "fee_amount": {
            "currency_code": "USD",
            "value": "-100.00"
        },
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {
            "currency_code": "USD",
            "value": "900.00"
        },
        "available_balance": {
            "currency_code": "USD",
            "value": "900.00"
        },
        "invoice_id": "1"
    },
    "payer_info": {
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {
            "alternate_full_name": "Acme, Inc."
        },
        "country_code": "US"
    },
    "shipping_info": {},
    "cart_info": {},
    "store_info": {},
    "auction_info": {},
    "incentive_info": {}
}"""
            % (
                self.today_isoformat,
                self.today_isoformat,
            )
        )
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
                "unique_import_id": "1234567890-%s" % (self.today_timestamp,),
            },
        )
        self.assertEqual(
            lines[1],
            {
                "date": self.today,
                "amount": "-100.00",
                "ref": "Fee for Invoice 1",
                "payment_ref": "Transaction fee for 1234567890: Payment for Invoice(s) 1",
                "partner_name": "PayPal",
                "unique_import_id": "1234567890-%s-FEE" % (self.today_timestamp,),
            },
        )

    def test_transaction_parse_4(self):
        lines = self.paypal_parse_transaction(
            """{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "%s",
        "transaction_updated_date": "%s",
        "transaction_amount": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "transaction_status": "S",
        "transaction_subject": "Payment for Invoice(s) 1",
        "ending_balance": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "available_balance": {
            "currency_code": "USD",
            "value": "1000.00"
        },
        "invoice_id": "1"
    },
    "payer_info": {
        "account_id": "1234567890",
        "email_address": "partner@example.com",
        "address_status": "Y",
        "payer_status": "N",
        "payer_name": {
            "alternate_full_name": "Acme, Inc."
        },
        "country_code": "US"
    },
    "shipping_info": {},
    "cart_info": {},
    "store_info": {},
    "auction_info": {},
    "incentive_info": {}
}"""
            % (
                self.today_isoformat,
                self.today_isoformat,
            )
        )
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
                "unique_import_id": "1234567890-%s" % (self.today_timestamp,),
            },
        )
