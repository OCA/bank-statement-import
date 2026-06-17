# Copyright 2026 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)
from unittest.mock import MagicMock, patch

from odoo.tests.common import SavepointCase

MODULE_PATH = "odoo.addons.account_statement_import_online_adyen"
ONLINE_PROVIDER = "%s.models.online_bank_statement_provider" % MODULE_PATH


class TestOnlineBankStatementProvider(SavepointCase):
    @classmethod
    def setUpClass(cls):
        super(TestOnlineBankStatementProvider, cls).setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {
                "company_id": cls.env.user.company_id.id,
                "name": "Adyen Online Test",
                "code": "AOT",
                "type": "bank",
                "bank_acc_number": "YOURCOMPANY_ACCOUNT",
                "adyen_merchant_account": "YOURCOMPANY_ACCOUNT",
                "currency_id": cls.env.ref("base.USD").id,
            }
        )
        cls.journal.write(
            {
                "bank_statements_source": "online",
                "online_bank_statement_provider": "adyen",
            }
        )
        cls.provider = cls.journal.online_bank_statement_provider_id
        cls.provider.write(
            {
                "api_base": (
                    "https://ca-test.adyen.com/reports/download/MerchantAccount"
                ),
                "download_file_name": "settlement_detail_report_batch_380.csv",
                "interval_type": "days",
                "interval_number": 1,
                "service": "adyen",
                "next_batch_number": 1,
            }
        )

    @patch(ONLINE_PROVIDER + ".requests")
    def test_adyen_get_settlement_details_file(self, mock_request):
        # mock the response
        content = self.provider._adyen_dummy_get_settlement_details_file()
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = content
        mock_request.get.return_value = mock_response
        # Actual download file name needs a replacement variable for batch number.
        self.provider.download_file_name = "settlement_detail_report_batch_%s.csv"
        result_content, filename = self.provider._adyen_get_settlement_details_file()
        self.assertEqual(len(content), len(result_content))
        batch_number = self.provider.next_batch_number
        expected_file_name = self.provider.download_file_name % batch_number
        self.assertIn(expected_file_name, filename)
