# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import _, api, fields, models


# pylint: disable=R7980
class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    auto_reconcile = fields.Boolean('Auto reconcile', default=True)

    @api.model
    def _create_bank_statement(self, stmt_vals):
        statement_id, notifications = super(
            AccountBankStatementImport, self
        )._create_bank_statement(stmt_vals)
        if not statement_id:
            return statement_id, notifications
        statement = self.env['account.bank.statement'].browse(statement_id)
        if (
                not statement.journal_id
                .statement_import_auto_reconcile_rule_ids or
                not self.auto_reconcile
        ):
            return statement_id, notifications
        reconcile_rules = statement.journal_id\
            .statement_import_auto_reconcile_rule_ids.get_rules()
        auto_reconciled_ids = []
        for line in statement.line_ids:
            for rule in reconcile_rules:
                if rule.reconcile(line):
                    auto_reconciled_ids.append(line.id)
                    break
        if auto_reconciled_ids:
            notifications.append({
                'type': 'warning',
                'message':
                _("%d transactions were reconciled automatically.") %
                len(auto_reconciled_ids),
                'details': {
                    'name': _('Automatically reconciled'),
                    'model': 'account.bank.statement.line',
                    'ids': auto_reconciled_ids,
                },
            })
        return statement_id, notifications
