# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import json
from unittest import mock
from urllib.error import HTTPError

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import common

_module_ns = 'odoo.addons.account_bank_statement_import_online_paypal'
_provider_class = (
    _module_ns
    + '.models.online_bank_statement_provider_paypal'
    + '.OnlineBankStatementProviderPayPal'
)


class FakeHTTPError(HTTPError):
    def __init__(self, content):
        self.content = content

    def read(self):
        return self.content.encode('utf-8')


class UrlopenRetValMock:
    def __init__(self, content, throw=False):
        self.content = content
        self.throw = throw

    def __enter__(self):
        return self

    def __exit__(self, type, value, tb):
        pass

    def read(self):
        if self.throw:
            raise FakeHTTPError(self.content)
        return self.content.encode('utf-8')


class TestAccountBankAccountStatementImportOnlinePayPal(
    common.TransactionCase
):

    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref('base.EUR')
        self.currency_usd = self.env.ref('base.USD')
        self.AccountJournal = self.env['account.journal']
        self.OnlineBankStatementProvider = self.env[
            'online.bank.statement.provider'
        ]
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementLine = self.env['account.bank.statement.line']

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
            _provider_class + '._paypal_get_token',
            return_value='--TOKEN--',
        )

    def test_good_token(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads("""{
    "scope": "https://uri.paypal.com/services/reporting/search/read",
    "access_token": "---TOKEN---",
    "token_type": "Bearer",
    "app_id": "APP-1234567890",
    "expires_in": 32400,
    "nonce": "---NONCE---"
}""", parse_float=Decimal)
        token = None
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            return_value=mocked_response,
        ):
            token = provider._paypal_get_token()
        self.assertEqual(token, '---TOKEN---')

    def test_bad_token_scope(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads("""{
    "scope": "openid https://uri.paypal.com/services/applications/webhooks",
    "access_token": "---TOKEN---",
    "token_type": "Bearer",
    "app_id": "APP-1234567890",
    "expires_in": 32400,
    "nonce": "---NONCE---"
}""", parse_float=Decimal)
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            return_value=mocked_response,
        ):
            with self.assertRaises(Exception):
                provider._paypal_get_token()

    def test_bad_token_type(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads("""{
    "scope": "https://uri.paypal.com/services/reporting/search/read",
    "access_token": "---TOKEN---",
    "token_type": "NotBearer",
    "app_id": "APP-1234567890",
    "expires_in": 32400,
    "nonce": "---NONCE---"
}""", parse_float=Decimal)
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            return_value=mocked_response,
        ):
            with self.assertRaises(Exception):
                provider._paypal_get_token()

    def test_no_token(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads("""{
        "scope": "https://uri.paypal.com/services/reporting/search/read",
        "token_type": "Bearer",
        "app_id": "APP-1234567890",
        "expires_in": 32400,
        "nonce": "---NONCE---"
    }""", parse_float=Decimal)
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            return_value=mocked_response,
        ):
            with self.assertRaises(Exception):
                provider._paypal_get_token()

    def test_no_data_on_monday(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response_1 = UrlopenRetValMock("""{
    "debug_id": "eec890ebd5798",
    "details": "xxxxxx",
    "links": "xxxxxx",
    "message": "Data for the given start date is not available.",
    "name": "INVALID_REQUEST"
}""", throw=True)
        mocked_response_2 = UrlopenRetValMock("""{
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
    "as_of_time": "2019-08-01T00:00:00+0000",
    "last_refresh_time": "2019-08-01T00:00:00+0000"
}""")
        with mock.patch(
            _provider_class + '._paypal_urlopen',
            side_effect=[mocked_response_1, mocked_response_2],
        ), self.mock_token():
            data = provider.with_context(
                test_account_bank_statement_import_online_paypal_monday=True,
            )._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertEqual(data, ([], {
            'balance_start': 0.75,
            'balance_end_real': 0.75,
        }))

    def test_error_handling_1(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = UrlopenRetValMock("""{
    "message": "MESSAGE",
    "name": "ERROR"
}""", throw=True)
        with mock.patch(
            _provider_class + '._paypal_urlopen',
            return_value=mocked_response,
        ):
            with self.assertRaises(UserError):
                provider._paypal_retrieve('https://url', '')

    def test_error_handling_2(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = UrlopenRetValMock("""{
    "error_description": "ERROR DESCRIPTION",
    "error": "ERROR"
}""", throw=True)
        with mock.patch(
            _provider_class + '._paypal_urlopen',
            return_value=mocked_response,
        ):
            with self.assertRaises(UserError):
                provider._paypal_retrieve('https://url', '')

    def test_empty_pull(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response_1 = json.loads("""{
    "transaction_details": [],
    "account_number": "1234567890",
    "start_date": "2019-08-01T00:00:00+0000",
    "end_date": "2019-08-01T00:00:00+0000",
    "last_refreshed_datetime": "2019-09-01T00:00:00+0000",
    "page": 1,
    "total_items": 0,
    "total_pages": 0
}""", parse_float=Decimal)
        mocked_response_2 = json.loads("""{
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
    "as_of_time": "2019-08-01T00:00:00+0000",
    "last_refresh_time": "2019-08-01T00:00:00+0000"
}""", parse_float=Decimal)
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            side_effect=[mocked_response_1, mocked_response_2],
        ), self.mock_token():
            data = provider._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertEqual(data, ([], {
            'balance_start': 0.75,
            'balance_end_real': 0.75,
        }))

    def test_ancient_pull(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads("""{
    "transaction_details": [],
    "account_number": "1234567890",
    "start_date": "2019-08-01T00:00:00+0000",
    "end_date": "2019-08-01T00:00:00+0000",
    "last_refreshed_datetime": "2019-09-01T00:00:00+0000",
    "page": 1,
    "total_items": 0,
    "total_pages": 0
}""", parse_float=Decimal)
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            return_value=mocked_response,
        ), self.mock_token():
            with self.assertRaises(Exception):
                provider._obtain_statement_data(
                    self.now - relativedelta(years=5),
                    self.now,
                )

    def test_pull(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'paypal',
        })

        provider = journal.online_bank_statement_provider_id
        mocked_response = json.loads("""{
    "transaction_details": [{
        "transaction_info": {
            "paypal_account_id": "1234567890",
            "transaction_id": "1234567890",
            "transaction_event_code": "T1234",
            "transaction_initiation_date": "2019-08-01T00:00:00+0000",
            "transaction_updated_date": "2019-08-01T00:00:00+0000",
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
            "transaction_initiation_date": "2019-08-02T00:00:00+0000",
            "transaction_updated_date": "2019-08-02T00:00:00+0000",
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
    "start_date": "2019-08-01T00:00:00+0000",
    "end_date": "2019-08-02T00:00:00+0000",
    "last_refreshed_datetime": "2019-09-01T00:00:00+0000",
    "page": 1,
    "total_items": 1,
    "total_pages": 1
}""", parse_float=Decimal)
        with mock.patch(
            _provider_class + '._paypal_retrieve',
            return_value=mocked_response,
        ), self.mock_token():
            data = provider._obtain_statement_data(
                datetime(2019, 8, 1),
                datetime(2019, 8, 2),
            )

        self.assertEqual(len(data[0]), 2)
        self.assertEqual(data[0][0], {
            'date': datetime(2019, 8, 1),
            'amount': '1000.00',
            'name': 'Invoice 1',
            'note': '1234567890: Payment for Invoice(s) 1',
            'partner_name': 'Acme, Inc.',
            'unique_import_id': '1234567890-1564617600',
        })
        self.assertEqual(data[0][1], {
            'date': datetime(2019, 8, 1),
            'amount': '-100.00',
            'name': 'Fee for Invoice 1',
            'note': 'Transaction fee for 1234567890: Payment for Invoice(s) 1',
            'partner_name': 'PayPal',
            'unique_import_id': '1234567890-1564617600-FEE',
        })
        self.assertEqual(data[1], {
            'balance_start': 0.0,
            'balance_end_real': 900.0,
        })

    def test_transaction_parse_1(self):
        lines = self.paypal_parse_transaction("""{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "2019-08-01T00:00:00+0000",
        "transaction_updated_date": "2019-08-01T00:00:00+0000",
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
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2019, 8, 1),
            'amount': '1000.00',
            'name': 'Invoice 1',
            'note': '1234567890: Payment for Invoice(s) 1',
            'partner_name': 'Acme, Inc.',
            'unique_import_id': '1234567890-1564617600',
        })

    def test_transaction_parse_2(self):
        lines = self.paypal_parse_transaction("""{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "2019-08-01T00:00:00+0000",
        "transaction_updated_date": "2019-08-01T00:00:00+0000",
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
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2019, 8, 1),
            'amount': '1000.00',
            'name': 'Invoice 1',
            'note': '1234567890: Payment for Invoice(s) 1',
            'partner_name': 'Acme, Inc.',
            'unique_import_id': '1234567890-1564617600',
        })

    def test_transaction_parse_3(self):
        lines = self.paypal_parse_transaction("""{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "2019-08-01T00:00:00+0000",
        "transaction_updated_date": "2019-08-01T00:00:00+0000",
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
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2019, 8, 1),
            'amount': '1000.00',
            'name': 'Invoice 1',
            'note': '1234567890: Payment for Invoice(s) 1',
            'partner_name': 'Acme, Inc.',
            'unique_import_id': '1234567890-1564617600',
        })
        self.assertEqual(lines[1], {
            'date': datetime(2019, 8, 1),
            'amount': '-100.00',
            'name': 'Fee for Invoice 1',
            'note': 'Transaction fee for 1234567890: Payment for Invoice(s) 1',
            'partner_name': 'PayPal',
            'unique_import_id': '1234567890-1564617600-FEE',
        })

    def test_transaction_parse_4(self):
        lines = self.paypal_parse_transaction("""{
    "transaction_info": {
        "paypal_account_id": "1234567890",
        "transaction_id": "1234567890",
        "transaction_event_code": "T1234",
        "transaction_initiation_date": "2019-08-01T00:00:00+0000",
        "transaction_updated_date": "2019-08-01T00:00:00+0000",
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
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2019, 8, 1),
            'amount': '1000.00',
            'name': 'Invoice 1',
            'note': '1234567890: Payment for Invoice(s) 1',
            'partner_name': 'Acme, Inc.',
            'unique_import_id': '1234567890-1564617600',
        })
