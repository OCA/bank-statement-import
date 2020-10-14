from odoo import api, fields, models


class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    info = fields.Char(string="Info", required=False, )
    debitor = fields.Char(string="Debitor", required=False, )
    creditor = fields.Char(string="Creditor", required=False, )


    def get_statement_line_for_reconciliation_widget(self):
        data = super(AccountBankStatementLine, self).get_statement_line_for_reconciliation_widget()
        data['info'] = self.info
        return data
