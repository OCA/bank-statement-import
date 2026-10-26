# Copyright 2026 Luca Orioli <lucaorioli@gmail.com>
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl).

import json

from odoo.tests import tagged

from odoo.addons.base.tests.common import BaseCommon


@tagged("post_install", "-at_install")
class TestTransactionDetails(BaseCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.journal = cls.env["account.journal"].create(
            {"name": "Bank", "type": "bank", "code": "TBNK"}
        )

    def _create_line(self, **values):
        return self.env["account.bank.statement.line"].create(
            {
                "journal_id": self.journal.id,
                "payment_ref": "payment",
                "amount": 100.0,
                **values,
            }
        )

    def test_transaction_details_from_json_raw_data(self):
        data = {"id": "txn_1", "payer": {"email": "jane@example.com"}}
        line = self._create_line(raw_data=json.dumps(data))
        self.assertEqual(line.transaction_details, data)

    def test_transaction_details_from_other_raw_data(self):
        """Raw data that is not JSON is only kept as raw data"""
        line = self._create_line(raw_data="{'id': 'txn_1'}")
        self.assertFalse(line.transaction_details)
        self.assertEqual(line.raw_data, "{'id': 'txn_1'}")

    def test_transaction_details_given(self):
        line = self._create_line(
            raw_data=json.dumps({"id": "txn_1"}),
            transaction_details={"id": "other"},
        )
        self.assertEqual(line.transaction_details, {"id": "other"})

    def test_common_fields(self):
        line = self._create_line(
            partner_email="jane@example.com",
            partner_country_id=self.env.ref("base.it").id,
            card_masked_number="**** 4242",
            card_expiry_date="2030-12-31",
            provider_url="https://example.com/txn_1",
        )
        self.assertEqual(line.partner_email, "jane@example.com")
        self.assertEqual(line.partner_country_id.code, "IT")
