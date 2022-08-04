from odoo import api, models


class AccountBankStatement(models.Model):

    _inherit = "account.bank.statement"

    @api.model_create_multi
    def create(self, vals):
        """ When we do import of bank statement lines will always create a new
        statement, If we want to re use an existing one then we need to be able
        to make the switch in this method in order that all new lines go to
        the statement we want to reuse """
        res = super(AccountBankStatement, self).create(vals)

        existing_st = self.env.context.get("reuse_import_st_id")
        if existing_st:
            existing_st = self.browse(existing_st)
            existing_st.line_ids |= res.line_ids
            res.unlink()
            return existing_st

        return res
