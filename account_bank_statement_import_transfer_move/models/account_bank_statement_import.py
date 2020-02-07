# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import models


class AccountBankStatementImport(models.TransientModel):

    _inherit = "account.bank.statement.import"

    def _create_bank_statements(self, stmts_vals):
        """ Create additional line in statement to set bank statement statement
        to 0 balance"""

        statement_line_ids, notifications = super()._create_bank_statements(stmts_vals)
        statements = self.env["account.bank.statement"].search(
            [("line_ids", "in", statement_line_ids)]
        )
        for statement in statements:
            amount = sum(statement.line_ids.mapped("amount"))
            if statement.journal_id.transfer_line:
                if amount != 0:
                    amount = -amount
                line = statement.line_ids.create(
                    {
                        "name": statement.name,
                        "amount": amount,
                        "statement_id": statement.id,
                        "date": statement.date,
                    }
                )
                statement_line_ids.append(line.id)
                statement.balance_end_real = statement.balance_start
            else:
                statement.balance_end_real = statement.balance_start + amount
        return statement_line_ids, notifications
