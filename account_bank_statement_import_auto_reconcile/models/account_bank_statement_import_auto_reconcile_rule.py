# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import _, api, exceptions, fields, models
from .account_bank_statement_import_auto_reconcile import\
    AccountBankStatementImportAutoReconcile as auto_reconcile_base


class AccountBankStatementImportAutoReconcileRule(models.Model):
    _name = 'account.bank.statement.import.auto.reconcile.rule'
    _description = 'Automatic reconciliation rule'

    rule_type = fields.Selection('_sel_rule_type', required=True)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    options = fields.Serialized('Options')

    @api.model
    def _sel_rule_type(self):
        model_names = [
            model for model in self.env.registry
            if self.env[model]._name != auto_reconcile_base._name and
            issubclass(self.env[model].__class__, auto_reconcile_base)
        ]
        return self.env['ir.model'].search([
            ('model', 'in', model_names),
        ]).mapped(lambda x: (x.model, x.name))

    @api.constrains('rule_type')
    def _check_rule_type(self):
        for this in self:
            if this.mapped(
                    'journal_id.statement_import_auto_reconcile_rule_ids'
            ).filtered(lambda x: x != this and x.rule_type == this.rule_type):
                raise exceptions.ValidationError(
                    _('Reconciliation rules must be unique per journal')
                )

    @api.multi
    def name_get(self):
        return [
            (this.id, self.env[this.rule_type]._description)
            for this in self
        ]
