# Copyright 2020 Florent de Labarre
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest import mock

from odoo import fields
from odoo.tests import common

_module_ns = 'odoo.addons.account_bank_statement_import_online_qonto'
_provider_class = (
    _module_ns
    + '.models.online_bank_statement_provider_qonto'
    + '.OnlineBankStatementProviderQonto'
)


class TestAccountBankAccountStatementImportOnlineQonto(
    common.TransactionCase
):

    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.currency_eur = self.env.ref('base.EUR')
        self.currency_usd = self.env.ref('base.USD')
        self.AccountJournal = self.env['account.journal']
        self.ResPartnerBank = self.env['res.partner.bank']
        self.OnlineBankStatementProvider = self.env[
            'online.bank.statement.provider'
        ]
        self.AccountBankStatement = self.env['account.bank.statement']
        self.AccountBankStatementLine = self.env['account.bank.statement.line']

        self.bank_account = self.ResPartnerBank.create(
            {'acc_number': 'FR0214508000302245362775K46',
             'partner_id': self.env.user.company_id.partner_id.id})
        self.journal = self.AccountJournal.create({
            'name': 'Bank',
            'type': 'bank',
            'code': 'BANK',
            'currency_id': self.currency_eur.id,
            'bank_statements_source': 'online',
            'online_bank_statement_provider': 'qonto',
            'bank_account_id': self.bank_account.id,
        })
        self.provider = self.journal.online_bank_statement_provider_id

        self.mock_slug = lambda: mock.patch(
            _provider_class + '._qonto_get_slug',
            return_value={'FR0214508000302245362775K46': 'qonto-1234-bank-account-1'},
        )
        self.mock_transaction = lambda: mock.patch(
            _provider_class + '._qonto_get_transactions',
            return_value={
                "transactions": [
                    {"transaction_id": "qonto-1234-1-transaction-3",
                     "amount": 1200.0,
                     "amount_cents": 120000,
                     "attachment_ids": [],
                     "local_amount": 1200.0,
                     "local_amount_cents": 120000,
                     "side": "credit",
                     "operation_type": "income",
                     "currency": "EUR",
                     "local_currency": "EUR",
                     "label": "INVOICE A",
                     "settled_at": "2020-04-16T07:01:55.503Z",
                     "emitted_at": "2020-04-16T05:01:55.000Z",
                     "updated_at": "2020-04-16T07:04:02.792Z",
                     "status": "completed",
                     "note": None,
                     "reference": "Ref 1233",
                     "vat_amount": None,
                     "vat_amount_cents": None,
                     "vat_rate": None,
                     "initiator_id": None,
                     "label_ids": [],
                     "attachment_lost": False,
                     "attachment_required": True},
                    {"transaction_id": "qonto-1234-1-transaction-2",
                     "amount": 1128.36, "amount_cents": 112836,
                     "attachment_ids": [],
                     "local_amount": 1128.36,
                     "local_amount_cents": 112836,
                     "side": "debit",
                     "operation_type": "transfer",
                     "currency": "EUR",
                     "local_currency": "EUR",
                     "label": "BILL A",
                     "settled_at": "2020-04-16T07:00:30.979Z",
                     "emitted_at": "2020-04-15T18:22:30.296Z",
                     "updated_at": "2020-04-16T07:03:01.125Z",
                     "status": "completed",
                     "note": None,
                     "reference": "Invoice",
                     "vat_amount": None,
                     "vat_amount_cents": None,
                     "vat_rate": None,
                     "initiator_id": "9b783957-85a6-404a-8320-a298781cb5fa",
                     "label_ids": [],
                     "attachment_lost": False,
                     "attachment_required": True}],
                "meta": {"current_page": 1,
                         "next_page": None,
                         "prev_page": None,
                         "total_pages": 1,
                         "total_count": 2,
                         "per_page": 100}},
        )

    def test_qonto(self):
        with self.mock_transaction(), self.mock_slug():
            lines, statement_values = self.provider._obtain_statement_data(
                datetime(2020, 4, 15),
                datetime(2020, 4, 17),
            )

        self.assertEqual(len(lines), 2)
