# -*- coding: utf-8 -*-
"""Add process_camt method to account.bank.statement.import."""
# © 2017 Compassion CH <http://www.compassion.ch>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from odoo import models, fields


class AccountBankStatementLine(models.Model):
    """Add process_camt method to account.bank.statement.import."""
    _inherit = 'account.bank.statement.line'

    partner_address = fields.Char()
    partner_account = fields.Char()
    partner_bic = fields.Char()

    def get_statement_line_for_reconciliation_widget(self):
        """ Returns the data required by the bank statement
        reconciliation widget to display a statement line
        """
        data = super(AccountBankStatementLine,
                     self).get_statement_line_for_reconciliation_widget()
        if self.partner_address:
            data['partner_address'] = self.partner_address
        if self.partner_account:
            data['partner_account'] = self.partner_account

        return data
