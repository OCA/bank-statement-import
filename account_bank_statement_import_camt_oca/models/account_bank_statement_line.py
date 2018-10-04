from odoo import models


class AccountBankStatementLine(models.Model):
    _inherit = "account.bank.statement.line"

    def get_reconciliation_proposition(self, excluded_ids=None):
        """ Overridden to try & identify a reconciliation move_line for the
            current statement line by using the reference to match a bank
            payment line.

            This works in the case where the bank_payment_line
            `communication_type` is set to 'normal', as we then get the CAMT
            Ntry's `EndToEndId` value in self.ref after parsing, which is the
            Odoo bank_payment_line name if the related pain.001 file was
            emitted through the OCA's bank-payment flow.
        """

        self.ensure_one()
        if not excluded_ids:
            excluded_ids = []

        sql_query = """
        SELECT aml.id
        FROM account_move_line aml
        JOIN account_payment_line apl ON apl.move_line_id = aml.id
        JOIN bank_payment_line bpl ON bpl.id = apl.bank_line_id
        WHERE bpl.name = %(ref)s
        """
        if excluded_ids:
            sql_query = sql_query + ' AND aml.id NOT IN %(excluded_ids)s'

        params = {
            'ref': self.ref,
            'excluded_ids': tuple(excluded_ids),
        }

        self.env.cr.execute(sql_query, params)
        results = self.env.cr.fetchone()
        if results:
            return self.env['account.move.line'].browse(results[0])

        return super().get_reconciliation_proposition(excluded_ids)
