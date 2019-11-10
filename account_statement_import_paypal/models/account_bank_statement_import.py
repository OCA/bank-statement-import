# Copyright 2014-2017 Akretion (http://www.akretion.com).
# Copyright 2019 Tecnativa - Vicent Cubells
# Copyright 2019 Brainbean Apps (https://brainbeanapps.com)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from odoo import api, fields, models

import logging
_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    paypal_mapping_id = fields.Many2one(
        string='PayPal mapping',
        comodel_name='account.bank.statement.import.paypal.mapping',
    )

    @api.multi
    def _parse_file(self, data_file):
        self.ensure_one()
        try:
            Parser = self.env['account.bank.statement.import.paypal.parser']
            return Parser.parse(
                self.paypal_mapping_id,
                data_file,
                self.filename
            )
        except:
            if self.env.context.get(
                    'account_bank_statement_import_paypal_test'):
                raise
            _logger.warning('PayPal parser error', exc_info=True)
        return super()._parse_file(data_file)
