from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestAccountStatementImportFile(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls, chart_template_ref=None):
        super().setUpClass(chart_template_ref=chart_template_ref)
        cls.eur_currency = cls.env.ref("base.EUR")
        cls.usd_currency = cls.env.ref("base.USD")
        cls.company = cls.env.company
        cls.bank_journal_eur = cls.env["account.journal"].create(
            {
                "name": "Bank EUR Test",
                "type": "bank",
                "code": "BNK_T",
                "currency_id": cls.eur_currency.id,
            }
        )

    def test_eur_journal_usd_foreign(self):
        statement_line = (
            self.env["account.bank.statement.line"]
            .with_context(from_stmt_import=True)
            .create(
                {
                    "journal_id": self.bank_journal_eur.id,
                    "amount": 100.00,
                    "foreign_currency_id": self.usd_currency.id,
                    "amount_currency": 110.00,
                }
            )
        )
        move = statement_line.move_id
        self.assertTrue(move)
        bank_line = move.line_ids.filtered(
            lambda line: line.account_id.account_type == "asset_cash"
        )
        counterpart_line = move.line_ids - bank_line
        self.assertEqual(counterpart_line.credit, 110.0)
        self.assertEqual(counterpart_line.amount_currency, -100.0)
        self.assertEqual(bank_line.debit, 110.0)
        self.assertEqual(bank_line.amount_currency, 100.0)
