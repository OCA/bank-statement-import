# Copyright 2020 Camptocamp SA
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, models


class AccountBankStatementImport(models.TransientModel):

    _inherit = "account.bank.statement.import"

    @api.model
    def _parse_file(self, data_file):
        """Enable testing of this functionality."""
        if self.env.context.get("account_bank_statement_import_transfer_move", False):
            return (
                None,
                "NL77ABNA0574908765",
                [
                    {
                        "balance_end_real": 15121.12,
                        "balance_start": 15568.27,
                        "date": "2014-01-05",
                        "name": "1234Test/1",
                        "transactions": [
                            {
                                "account_number": "NL46ABNA0499998748",
                                "amount": -754.25,
                                "date": "2014-01-05",
                                "name": "Insurance policy 857239PERIOD 01.01.2014 - "
                                "31.12.2014",
                                "note": "MKB Insurance 859239PERIOD 01.01.2014 - "
                                "31.12.2014",
                                "partner_name": "INSURANCE COMPANY TESTX",
                                "ref": "435005714488-ABNO33052620",
                            },
                        ],
                    }
                ],
            )
        return super()._parse_file(data_file)

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
