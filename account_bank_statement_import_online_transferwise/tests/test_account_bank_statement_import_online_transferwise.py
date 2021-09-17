# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020-2021 CorporateHub (https://corporatehub.eu)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from dateutil.relativedelta import relativedelta
from decimal import Decimal
import json
from unittest import mock
from urllib.error import HTTPError

from odoo.tests import common
from odoo import fields

_module_ns = 'odoo.addons.account_bank_statement_import_online_transferwise'
_provider_class = (
    _module_ns
    + '.models.online_bank_statement_provider_transferwise'
    + '.OnlineBankStatementProviderTransferwise'
)


class MockedResponse:

    class Headers(dict):
        def get_content_charset(self):
            return None

    def __init__(self, data=None, exception=None):
        self.data = data
        self.exception = exception
        self.headers = MockedResponse.Headers()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        pass

    def read(self):
        if self.exception is not None:
            raise self.exception()
        return self.data


class TestAccountBankAccountStatementImportOnlineTransferwise(
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
        self.transferwise_parse_transaction = lambda payload: (
            Provider._transferwise_transaction_to_lines(
                Provider._transferwise_preparse_transaction(
                    json.loads(
                        payload,
                        parse_float=Decimal,
                    )
                )
            )
        )
        self.response_balance = MockedResponse(data="""[
            {
                "id": 42,
                "balances": [
                    {
                        "currency": "EUR"
                    }
                ]
            }
        ]""".encode())
        self.response_ott = MockedResponse(exception=lambda: HTTPError(
            'https://wise.com/',
            403,
            '403',
            {
                'X-2FA-Approval-Result': 'REJECTED',
                'X-2FA-Approval': '0123456789',
            },
            None,
        ))
        self.response_transactions = MockedResponse(data="""{
            "transactions": [],
            "endOfStatementBalance": {
                "value": 42.00,
                "currency": "EUR"
            }
        }""".encode())

    def test_values_transferwise_profile(self):
        mocked_response = json.loads(
            """[
    {
        "id": 1234567890,
        "type": "personal",
        "details": {
            "firstName": "Alexey",
            "lastName": "Pelykh"
        }
    },
    {
        "id": 1234567891,
        "type": "business",
        "details": {
            "name": "Brainbean Apps OÜ"
        }
    }
]""", parse_float=Decimal)
        values_transferwise_profile = []
        with mock.patch(
            _provider_class + '._transferwise_retrieve',
            return_value=mocked_response,
        ):
            values_transferwise_profile = (
                self.OnlineBankStatementProvider.with_context({
                    'api_base': 'https://example.com',
                    'api_key': 'dummy',
                }).values_transferwise_profile()
            )
        self.assertEqual(
            values_transferwise_profile,
            [
                ('1234567890', 'Alexey Pelykh (personal)'),
                ('1234567891', 'Brainbean Apps OÜ'),
            ]
        )

    def test_values_transferwise_profile_no_key(self):
        values_transferwise_profile = (
            self.OnlineBankStatementProvider.with_context({
                'api_base': 'https://example.com',
            }).values_transferwise_profile()
        )
        self.assertEqual(values_transferwise_profile, [])

    def test_values_transferwise_profile_error(self):
        values_transferwise_profile = []
        with mock.patch(
            _provider_class + '._transferwise_retrieve',
            side_effect=lambda: Exception(),
        ):
            values_transferwise_profile = (
                self.OnlineBankStatementProvider.with_context({
                    'api_base': 'https://example.com',
                    'api_key': 'dummy',
                }).values_transferwise_profile()
            )
        self.assertEqual(values_transferwise_profile, [])

    def test_pull(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'transferwise',
        })

        provider = journal.online_bank_statement_provider_id
        provider.origin = '1234567891'

        def mock_response(url, api_key, private_key=None):
            if '/borderless-accounts?profileId=1234567891' in url:
                payload = """[
    {
        "id": 42,
        "balances": [
            {
                "currency": "EUR"
            }
        ]
    }
]"""
            elif '/borderless-accounts/42/statement.json' in url:
                payload = """{
    "transactions": [],
    "endOfStatementBalance": {
        "value": 42.00,
        "currency": "EUR"
    }
}"""
            return json.loads(payload, parse_float=Decimal)
        with mock.patch(
            _provider_class + '._transferwise_retrieve',
            side_effect=mock_response,
        ):
            data = provider._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertEqual(len(data[0]), 0)
        self.assertEqual(data[1]['balance_start'], 42.0)
        self.assertEqual(data[1]['balance_end_real'], 42.0)

    def test_pull_no_data(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'transferwise',
        })

        provider = journal.online_bank_statement_provider_id
        provider.origin = '1234567891'
        provider.password = 'API_KEY'

        with mock.patch(
            _provider_class + '._transferwise_retrieve',
            return_value=[],
        ):
            data = provider._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertFalse(data)

    def test_update_public_key(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'transferwise',
        })

        provider = journal.online_bank_statement_provider_id
        provider.origin = '1234567891'
        provider.password = 'API_KEY'

        with common.Form(provider) as provider_form:
            provider_form.certificate_private_key = """
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAxC7aYWigCwPIB4mfyLpsALYPnqDm3/IC8I/3GdEwfK8eqXoF
sU1BHnVytFycBDEObmJ2Acpxe8Dk61FnbWPrrl6rXVnXfIRqfFl94TvgwFsuwG7u
8crncD6gPfe1QGkEykHcfBURr74OcSE8590ngNJcKMGvac0cuyZ2/NEszTw7EFJg
obpMWjp0m5ItgZ/UNsPLR/D4gFE9vZz7a4+FYQMa9Wbv+xaVxUS6z9rQCJfUQx7N
iih4etIvAafbfAnX6rFv8PwPzz+XvexPWWJxnbS4iV1LN2atrPDxqw73g5hc3W88
a0V2AVubtxhw9L2VK1VmRb/gnqsZpRXhDPSUIwIDAQABAoIBAQCMvnRLV80hudfC
mJh6YEvlgrfX/OVFmpFDVnVXHz2i5dugiHsXBS6HlIjzHlGLrEoHJTo19K/PscZJ
kEAcOYg2s5JLSY4PtcvTZDyr3tJSDdiPk8Z2zzOU0kkRy+lLyUv3cqKknlTu+PHR
daAFVCLoB4K4dqPKyq0nEuRgYgy7O42SPBY5DHgWYBKqkYGlTu+ImwpDD9unbv3e
mwvdcBCp9hAlYAArc1Ip/6aUkZdKxJYgVhovruaH309yuOmBfAEgguhsy3vR18t5
IZXbAF3C6iXCQXi8l+S1NUu8XWPLEavldb+ZA2hI2L+NPSBVIYqhI4jDiI7lfs1c
HE8BRsRpAoGBAO6BnK3qD8sRvg6JsrBhppoIGsudOdpZ/KVp9ZpYCBJNJmfrkqLR
bWx1KF2UjAoYUmaKDTS2GP8JQd7X2n4T5LX8q+7iG9/wzdSWZYZuBOnjvWlNyJu4
OiUKX4aEgdvZHiuEIin5xTP98/c5LTZXwM3bq8IrOXEz8LBLLPrTCGRvAoGBANKS
i3cn1jtVirJWbvhSIjjqhpfuZN0361FB6j1Aho+7z0WVd4NQjPQqA6cAqnWoa/kj
cX0X8Ncu5eHqf6CuW+HsQda3yp3bvCXi1Yc2nKBTHnWtMm721O4ZW6rbaALzBZYW
qeJr0m9pNlfCAL0INTcy7IVAtqcCJ/7CEN6Hjm2NAoGAIGSgKArDLFxziLvw9f29
R+xT31WyVtKj+r9iaR0Ns5ag4bpgBxcUmodq/RLA1lopTt3vHzqgOHtEZATDGx6O
kJ0JqP8ys/6bpgTrMw/cQPv6bMPwvB2QYBmBkd6LWJWrgFOI5FSVEROrv+cXGetf
N1ZfhJakTZi1VuxO5p4k5KcCgYAZS9OHR/jbfeZAkFOabzt/POVYYSIq1SnmxBVg
sFy57aTzxgXqd4XHWzi/GjxgEBCQiGp8zaB4KUEih6o3YlrVZC1wnvmvRxNuNbbT
HINqWzHgjyLs46gmxlMVzm/LUuiL5EMaWTuZeLk3h63RB6hk7jAtvd1zaLXnS+b8
5Kn+jQKBgQCDeMO6rvB2rbfqSbHvPPuTru1sPIsJBKm1YZpXTFI+VMjwtk7+meYb
UQnfZ1t5rjp9q4LEcRYuSa+PfifIkM6p+wMHVQhtltUCzXWWRYkLkmQrBWKu+qiP
edF6byMgXSzgOWYuRPXwmHpBQV0GiexQUAxVyUzaVWfil69LaFfXaw==
-----END RSA PRIVATE KEY-----
            """

        self.assertTrue(provider.certificate_public_key)

    def test_sca(self):
        journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'transferwise',
        })

        provider = journal.online_bank_statement_provider_id
        provider.origin = '1234567891'
        provider.password = 'API_KEY'
        provider.button_transferwise_generate_key()

        with mock.patch(
            'urllib.request.urlopen',
            side_effect=[
                self.response_balance,
                self.response_ott,
                self.response_transactions,
                self.response_transactions,
                self.response_transactions,
            ],
        ):
            data = provider._obtain_statement_data(
                self.now - relativedelta(hours=1),
                self.now,
            )

        self.assertEqual(len(data[0]), 0)
        self.assertEqual(data[1]['balance_start'], 42.0)
        self.assertEqual(data[1]['balance_end_real'], 42.0)

    def test_transaction_parse_1(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "CREDIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": 0.42,
        "currency": "EUR"
    },
    "totalFees": {
        "value": 0.00,
        "currency": "EUR"
    },
    "details": {
        "type": "DEPOSIT",
        "description": "Received money from SENDER with reference REF-XYZ",
        "senderName": "SENDER",
        "senderAccount": "XX00 0000 0000 0000",
        "paymentReference": "REF-XYZ"
    },
    "exchangeDetails": null,
    "runningBalance": {
        "value": 0.42,
        "currency": "EUR"
    },
    "referenceNumber": "TRANSFER-123456789"
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'amount': '0.42',
            'name': 'REF-XYZ',
            'note': (
                'TRANSFER-123456789: Received money from SENDER with reference'
                ' REF-XYZ'
            ),
            'partner_name': 'SENDER',
            'account_number': 'XX00 0000 0000 0000',
            'unique_import_id': 'CREDIT-TRANSFER-123456789-946684800',
        })

    def test_transaction_parse_2(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "DEBIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": -200.60,
        "currency": "EUR"
    },
    "totalFees": {
        "value": 0.60,
        "currency": "EUR"
    },
    "details": {
        "type": "TRANSFER",
        "description": "Sent money to John Doe",
        "recipient": {
            "name": "John Doe",
            "bankAccount": "XX00 0000 0000 0000"
        },
        "paymentReference": "INVOICE 42-01"
    },
    "exchangeDetails": null,
    "runningBalance": {
        "value": 100.42,
        "currency": "EUR"
    },
    "referenceNumber": "TRANSFER-123456789"
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'amount': '-200.00',
            'name': 'INVOICE 42-01',
            'note': 'TRANSFER-123456789: Sent money to John Doe',
            'partner_name': 'John Doe',
            'account_number': 'XX00 0000 0000 0000',
            'unique_import_id': 'DEBIT-TRANSFER-123456789-946684800',
        })
        self.assertEqual(lines[1], {
            'date': datetime(2000, 1, 1),
            'amount': '-0.60',
            'name': 'Fee for TRANSFER-123456789',
            'note': 'Transaction fee for TRANSFER-123456789',
            'partner_name': 'Wise (former TransferWise)',
            'unique_import_id': 'DEBIT-TRANSFER-123456789-946684800-FEE',
        })

    def test_transaction_parse_3(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "DEBIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": -123.45,
        "currency": "USD"
    },
    "totalFees": {
        "value": 0.00,
        "currency": "USD"
    },
    "details": {
        "type": "CARD",
        "description":
            "Card transaction of 1234.56 USD issued by Paypal *XX CITY",
        "amount": {
            "value": 1234.56,
            "currency": "USD"
        },
        "category": "Professional Services not elsewh",
        "merchant": {
            "name": "Paypal *XX",
            "firstLine": null,
            "postCode": "12345",
            "city": "CITY",
            "state": null,
            "country": "GB",
            "category": "Professional Services not elsewh"
        }
    },
    "exchangeDetails": null,
    "runningBalance": {
        "value": 0.00,
        "currency": "USD"
    },
    "referenceNumber": "CARD-123456789"
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'amount': '-123.45',
            'name': (
                'Card transaction of 1234.56 USD issued by Paypal *XX CITY'
            ),
            'note': (
                'CARD-123456789: Card transaction of 1234.56 USD issued by '
                'Paypal *XX CITY'
            ),
            'partner_name': 'Paypal *XX',
            'unique_import_id': 'DEBIT-CARD-123456789-946684800',
        })

    def test_transaction_parse_4(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "DEBIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": -456.78,
        "currency": "EUR"
    },
    "totalFees": {
        "value": 1.23,
        "currency": "EUR"
    },
    "details": {
        "type": "CARD",
        "description":
            "Card transaction of 1234.56 USD issued by Paypal *XX CITY",
        "amount": {
            "value": 1234.56,
            "currency": "USD"
        },
        "category": "Professional Services not elsewh",
        "merchant": {
            "name": "Paypal *XX",
            "firstLine": null,
            "postCode": "12345",
            "city": "CITY",
            "state": null,
            "country": "GB",
            "category": "Professional Services not elsewh"
        }
    },
    "exchangeDetails": {
        "toAmount": {
            "value": 567.89,
            "currency": "USD"
        },
        "fromAmount": {
            "value": 456.78,
            "currency": "EUR"
        },
        "rate": 1.12260
    },
    "runningBalance": {
        "value": 0.00,
        "currency": "EUR"
    },
    "referenceNumber": "CARD-123456789"
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'amount': '-455.55',
            'name': (
                'Card transaction of 1234.56 USD issued by Paypal *XX CITY'
            ),
            'note': (
                'CARD-123456789: Card transaction of 1234.56 USD issued by'
                ' Paypal *XX CITY'
            ),
            'partner_name': 'Paypal *XX',
            'unique_import_id': 'DEBIT-CARD-123456789-946684800',
            'amount_currency': '-567.89',
            'currency_id': self.currency_usd.id,
        })
        self.assertEqual(lines[1], {
            'date': datetime(2000, 1, 1),
            'amount': '-1.23',
            'name': 'Fee for CARD-123456789',
            'note': 'Transaction fee for CARD-123456789',
            'partner_name': 'Wise (former TransferWise)',
            'unique_import_id': 'DEBIT-CARD-123456789-946684800-FEE',
        })

    def test_transaction_parse_5(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "DEBIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": -270.55,
        "currency": "EUR"
    },
    "totalFees": {
        "value": 5.21,
        "currency": "EUR"
    },
    "details": {
        "type": "TRANSFER",
        "description": "Sent money to Jane Doe",
        "recipient": {
            "name": "Jane Doe",
            "bankAccount": "(ADBCDEF) 0000000000000000"
        },
        "paymentReference": "Invoice A from DD MMM YYYY"
    },
    "exchangeDetails": {
        "toAmount": {
            "value": 297.00,
            "currency": "USD"
        },
        "fromAmount": {
            "value": 265.34,
            "currency": "EUR"
        },
        "rate": 1.11930
    },
    "runningBalance": {
        "value": 2360.43,
        "currency": "EUR"
    },
    "referenceNumber": "TRANSFER-123456789"
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'name': 'Invoice A from DD MMM YYYY',
            'note': 'TRANSFER-123456789: Sent money to Jane Doe',
            'partner_name': 'Jane Doe',
            'account_number': '(ADBCDEF) 0000000000000000',
            'amount': '-265.34',
            'amount_currency': '-297.00',
            'currency_id': self.currency_usd.id,
            'unique_import_id': 'DEBIT-TRANSFER-123456789-946684800',
        })
        self.assertEqual(lines[1], {
            'date': datetime(2000, 1, 1),
            'name': 'Fee for TRANSFER-123456789',
            'note': 'Transaction fee for TRANSFER-123456789',
            'partner_name': 'Wise (former TransferWise)',
            'amount': '-5.21',
            'unique_import_id': 'DEBIT-TRANSFER-123456789-946684800-FEE',
        })

    def test_transaction_parse_6(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "CREDIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": 5000.00,
        "currency": "EUR"
    },
    "totalFees": {
        "value": 0.00,
        "currency": "EUR"
    },
    "details": {
        "type": "MONEY_ADDED",
        "description": "Topped up balance"
    },
    "exchangeDetails": null,
    "runningBalance": {
        "value": 7071.13,
        "currency": "EUR"
    },
    "referenceNumber": "TRANSFER-123456789"
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'name': 'Topped up balance',
            'note': 'TRANSFER-123456789: Topped up balance',
            'amount': '5000.00',
            'unique_import_id': 'CREDIT-TRANSFER-123456789-946684800',
        })

    def test_transaction_parse_7(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "CREDIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": 6.93,
        "currency": "EUR"
    },
    "totalFees": {
        "value": 0.00,
        "currency": "EUR"
    },
    "details": {
        "type": "CONVERSION",
        "description": "Converted 7.93 USD to 6.93 EUR",
        "sourceAmount": {
            "value": 7.93,
            "currency": "USD"
        },
        "targetAmount": {
            "value": 6.93,
            "currency": "EUR"
        },
        "rate": 0.87944162
    },
    "exchangeDetails": {
        "toAmount": {
            "value": 6.93,
            "currency": "EUR"
        },
        "fromAmount": {
            "value": 7.93,
            "currency": "USD"
        },
        "rate": 0.87944
    },
    "runningBalance": {
        "value": 255.00,
        "currency": "EUR"
    },
    "referenceNumber": "BALANCE-123456789"
}""")
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'name': 'Converted 7.93 USD to 6.93 EUR',
            'note': 'BALANCE-123456789: Converted 7.93 USD to 6.93 EUR',
            'amount': '6.93',
            'amount_currency': '7.93',
            'currency_id': self.currency_usd.id,
            'unique_import_id': 'CREDIT-BALANCE-123456789-946684800',
        })

    def test_transaction_parse_8(self):
        lines = self.transferwise_parse_transaction("""{
    "type": "DEBIT",
    "date": "2000-01-01T00:00:00.000Z",
    "amount": {
        "value": -7.93,
        "currency": "USD"
    },
    "totalFees": {
        "value": 0.05,
        "currency": "USD"
    },
    "details": {
        "type": "CONVERSION",
        "description": "Converted 7.93 USD to 6.93 EUR",
        "sourceAmount": {
            "value": 7.93,
            "currency": "USD"
        },
        "targetAmount": {
            "value": 6.93,
            "currency": "EUR"
        },
        "rate": 0.87944162
    },
    "exchangeDetails": {
        "toAmount": {
            "value": 6.93,
            "currency": "EUR"
        },
        "fromAmount": {
            "value": 7.93,
            "currency": "USD"
        },
        "rate": 0.87944
    },
    "runningBalance": {
        "value": 0.00,
        "currency": "USD"
    },
    "referenceNumber": "BALANCE-123456789"
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'name': 'Converted 7.93 USD to 6.93 EUR',
            'note': 'BALANCE-123456789: Converted 7.93 USD to 6.93 EUR',
            'amount': '-7.88',
            'amount_currency': '-6.93',
            'currency_id': self.currency_eur.id,
            'unique_import_id': 'DEBIT-BALANCE-123456789-946684800',
        })
        self.assertEqual(lines[1], {
            'date': datetime(2000, 1, 1),
            'name': 'Fee for BALANCE-123456789',
            'note': 'Transaction fee for BALANCE-123456789',
            'amount': '-0.05',
            'partner_name': 'Wise (former TransferWise)',
            'unique_import_id': 'DEBIT-BALANCE-123456789-946684800-FEE',
        })

    def test_transaction_parse_9(self):
        lines = self.transferwise_parse_transaction("""{
            "type": "CREDIT",
            "date": "2000-01-01T00:00:00.000Z",
            "amount": {
                "value": 25.00,
                "currency": "USD"
            },
            "totalFees": {
                "value": 0.68,
                "currency": "USD"
            },
            "details": {
                "type": "MONEY_ADDED",
                "description": "Topped up balance"
            },
            "exchangeDetails": null,
            "runningBalance": {
                "value": 25.68,
                "currency": "USD"
            },
            "referenceNumber": "TRANSFER-123456789"
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'name': 'Topped up balance',
            'note': 'TRANSFER-123456789: Topped up balance',
            'amount': '25.68',
            'unique_import_id': 'CREDIT-TRANSFER-123456789-946684800',
        })
        self.assertEqual(lines[1], {
            'date': datetime(2000, 1, 1),
            'name': 'Fee for TRANSFER-123456789',
            'note': 'Transaction fee for TRANSFER-123456789',
            'amount': '-0.68',
            'partner_name': 'Wise (former TransferWise)',
            'unique_import_id': 'CREDIT-TRANSFER-123456789-946684800-FEE',
        })

    def test_transaction_parse_10(self):
        lines = self.transferwise_parse_transaction("""{
            "type": "CREDIT",
            "date": "2000-01-01T00:00:00.000Z",
            "amount": {
                "value": 1804.33,
                "currency": "USD"
            },
            "totalFees": {
                "value": 4.33,
                "currency": "USD"
            },
            "details": {
                "type": "TRANSFER",
                "description": "Sent money to Acme Inc.",
                "recipient": {
                    "name": "Acme Inc."
                }
            },
            "exchangeDetails": null,
            "runningBalance": {
                "value": 1804.33,
                "currency": "USD"
            },
            "referenceNumber": "TRANSFER-123456789"
}""")
        self.assertEqual(len(lines), 2)
        self.assertEqual(lines[0], {
            'date': datetime(2000, 1, 1),
            'name': 'Sent money to Acme Inc.',
            'note': 'TRANSFER-123456789: Sent money to Acme Inc.',
            'partner_name': 'Acme Inc.',
            'amount': '1800.00',
            'unique_import_id': 'CREDIT-TRANSFER-123456789-946684800',
        })
        self.assertEqual(lines[1], {
            'date': datetime(2000, 1, 1),
            'name': 'Fee for TRANSFER-123456789',
            'note': 'Transaction fee for TRANSFER-123456789',
            'amount': '4.33',
            'partner_name': 'Wise (former TransferWise)',
            'unique_import_id': 'CREDIT-TRANSFER-123456789-946684800-FEE',
        })
