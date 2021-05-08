# Copyright 2019 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import base64
import logging

from odoo import api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.bank.statement.import"

    check_journal = fields.Boolean(default=True)
    check_message = fields.Char(readonly=True)
    force_journal = fields.Boolean(
        string="Do you want to force this import ?", default=False
    )

    @api.multi
    def import_file(self):
        """ Override to make the import in 2 step.

        To provide to user possiblity to bypass the journal check.
        """
        self.ensure_one()
        currency_code, account_number, stmts_vals = self.with_context(
            active_id=self.ids[0]
        )._parse_file(base64.b64decode(self.data_file))
        if self.check_journal:
            try:
                self._find_additional_data(currency_code, account_number)
                # _find_additional_data() call _check_journal_bank_account()
                # so the self.check_journal value can evolve
            except UserError as u_error:
                if not self.check_journal:
                    msg = u_error.args[0]
                    _logger.info(msg)
                    self.check_message = str(msg)
                    action = self.env.ref(
                        "account_bank_statement_import."
                        "action_account_bank_statement_import"
                    ).read([])[0]
                    action["res_id"] = self.id
                    return action
        return super().import_file()

    def _check_journal_bank_account(self, journal, account_number):
        check = super()._check_journal_bank_account(journal, account_number)
        if self.check_journal:
            self.check_journal = False
        if self.force_journal:
            return True
        return check
