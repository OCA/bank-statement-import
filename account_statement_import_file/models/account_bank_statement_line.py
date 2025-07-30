from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def _get_amounts_with_currencies(self):
        (
            company_amount,
            company_currency,
            journal_amount,
            journal_currency,
            transaction_amount,
            foreign_currency,
        ) = super()._get_amounts_with_currencies()
        if self.env.context.get("from_stmt_import", False) and self.foreign_currency_id:
            if self.foreign_currency_id == company_currency:
                company_currency = self.journal_id.company_id.currency_id
                journal_currency = self.journal_id.currency_id or company_currency
                company_amount = self.amount_currency
                foreign_currency = journal_currency
                transaction_amount = self.amount
            elif journal_currency == company_currency:
                journal_amount = self.amount_currency
                journal_currency = foreign_currency
        return (
            company_amount,
            company_currency,
            journal_amount,
            journal_currency,
            transaction_amount,
            foreign_currency,
        )
