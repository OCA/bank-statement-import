# Copyright 2020 Tecnativa - João Marques
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3.0

from odoo.tests import common


class TestAccountBankStatementClearPartner(common.SavepointCase):
    @classmethod
    def setup_multi_currency_data(cls, default_values=None, rate2016=3.0, rate2017=2.0):
        default_values = default_values or {}
        foreign_currency = cls.env["res.currency"].search(
            [("active", "=", False)], limit=1
        )
        rate1 = cls.env["res.currency.rate"].create(
            {
                "name": "2016-01-01",
                "rate": rate2016,
                "currency_id": foreign_currency.id,
                "company_id": cls.env.company.id,
            }
        )
        rate2 = cls.env["res.currency.rate"].create(
            {
                "name": "2017-01-01",
                "rate": rate2017,
                "currency_id": foreign_currency.id,
                "company_id": cls.env.company.id,
            }
        )
        return {
            "currency": foreign_currency,
            "rates": rate1 + rate2,
        }

    @classmethod
    def setUpClass(cls):
        super(TestAccountBankStatementClearPartner, cls).setUpClass()
        cls.partner_1 = cls.env["res.partner"].create({"name": "Partner 1"})
        cls.partner_2 = cls.env["res.partner"].create({"name": "Partner 2"})
        cls.currency_data = cls.setup_multi_currency_data()
        cls.account_type_1 = cls.env["account.account.type"].create(
            {"name": "Test Account Type 1", "type": "other", "internal_group": "income"}
        )
        cls.account_1 = cls.env["account.account"].create(
            {
                "name": "Test Account 1",
                "code": "AAAAAAAAAAAAAAAA",
                "user_type_id": cls.account_type_1.id,
            }
        )
        cls.sequence_1 = cls.env["ir.sequence"].create({"name": "Test Sequence 1"})
        cls.journal_1 = cls.env["account.journal"].create(
            {
                "name": "Test Journal 1",
                "type": "bank",
                "secure_sequence_id": cls.sequence_1.id,
            }
        )
        cls.statement_1 = cls.env["account.bank.statement"].create(
            {"name": "Test Bank Statement 1", "journal_id": cls.journal_1.id}
        )

        cls.currency_2 = cls.currency_data["currency"]
        line_obj = cls.env["account.bank.statement.line"]
        cls.st_line_w_partner_not_reconciled = line_obj.create(
            {
                "name": "Test Account Bank Statement 1",
                "statement_id": cls.statement_1.id,
                "partner_id": cls.partner_1.id,
                "payment_ref": "REF-TEST-1",
                "foreign_currency_id": cls.currency_2.id,
                "amount": 1250.0,
                "amount_currency": 2500.0,
            }
        )
        cls.st_line_wo_partner_not_reconciled = line_obj.create(
            {
                "name": "Test Account Bank Statement 2",
                "statement_id": cls.statement_1.id,
                "partner_id": False,
                "payment_ref": "REF-TEST-2",
            }
        )
        cls.st_line_w_partner_reconciled = line_obj.create(
            {
                "name": "Test Account Bank Statement 3",
                "statement_id": cls.statement_1.id,
                "partner_id": cls.partner_2.id,
                "payment_ref": "REF-TEST-3",
            }
        )

        cls.account_move_1 = cls.env["account.move"].create(
            {
                "move_type": "entry",
                "journal_id": cls.journal_1.id,
                "invoice_line_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "50 to pay",
                            "account_id": cls.account_1.id,
                            "amount_residual": 1,
                            "statement_line_id": cls.st_line_w_partner_reconciled.id,
                        },
                    )
                ],
            }
        )

    def test_bank_statements_clear_partner(self):
        self.statement_1.clear_partners()
        # Confirm statement_line_1 has no parter
        self.assertFalse(self.st_line_w_partner_not_reconciled.partner_id)
        # Confirm statement_line_3 still has partner because it was already reconciled
        self.assertTrue(self.st_line_w_partner_reconciled.partner_id)
