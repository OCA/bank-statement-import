# Copyright 2023 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from datetime import datetime
from unittest import mock

from dateutil.relativedelta import relativedelta

from odoo import fields
from odoo.tests import common

_module_ns = "odoo.addons.account_statement_import_online_ofx"
_provider_class = (
    _module_ns
    + ".models.online_bank_statement_provider_ofx"
    + ".OnlineBankStatementProviderOFX"
)


class TestAccountBankAccountStatementImportOnlineOFX(common.TransactionCase):
    def setUp(self):
        super().setUp()

        self.now = fields.Datetime.now()
        self.today = datetime(self.now.year, self.now.month, self.now.day)
        self.yesterday = self.today - relativedelta(days=1)
        self.AccountJournal = self.env["account.journal"]
        self.OnlineBankStatementProvider = self.env["online.bank.statement.provider"]
        self.AccountBankStatement = self.env["account.bank.statement"]
        self.AccountBankStatementLine = self.env["account.bank.statement.line"]
        self.OfxInstitutionLine = self.env["ofx.institution.line"]
        self.ofx_institute = self.env["ofx.institution"].create(
            {"name": "Test", "nickname": "Test", "ofxhome_id": 1}
        )

    def test_import_online_ofx(self):

        provider_model = self.env["online.bank.statement.provider"]
        active_id = self.env.context.get("active_id")
        provider = provider_model.browse(active_id)

        # Create OFX institution line in OFX provider
        self.OfxInstitutionLine.create(
            {
                "institution_id": self.ofx_institute.id,
                "username": "Test",
                "password": "Test",
                "bankid": "1234",
                "provider_id": provider.id,
                "account_id": "1234",
            }
        )

        # import statement

        mocked_response = [
            {
                "date": self.today,
                "payment_ref": "BANKCARD 12345678",
                "amount": 5645.07,
                "unique_import_id": "202302211",
            },
            {
                "date": self.today,
                "payment_ref": "ELECTRONIC IMAGE DEPOSIT",
                "amount": 2874.91,
                "unique_import_id": "202302212",
            },
            {
                "date": self.today,
                "payment_ref": "BANKCARD 567890123",
                "amount": 1269.18,
                "unique_import_id": "202302213",
            },
        ], {}
        with mock.patch(
            _provider_class + "._obtain_statement_data",
            return_value=mocked_response,
        ):
            data = provider._obtain_statement_data(
                self.yesterday,
                self.today,
            )

        self.assertEqual(len(data[0]), 3)
        self.assertEqual(
            data[0][1],
            {
                "date": self.today,
                "payment_ref": "ELECTRONIC IMAGE DEPOSIT",
                "amount": 2874.91,
                "unique_import_id": "202302212",
            },
        )
        self.assertEqual(data[1], {})
