# -*- coding: utf-8 -*-
# © 2017 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from lxml import etree
from openerp import _, api, exceptions, fields, models, tools
from .account_bank_statement_import_auto_reconcile import\
    AccountBankStatementImportAutoReconcile as auto_reconcile_base


class AccountBankStatementImportAutoReconcileRule(models.Model):
    _name = 'account.bank.statement.import.auto.reconcile.rule'
    _description = 'Automatic reconciliation rule'

    rule_type = fields.Selection('_sel_rule_type', required=True)
    journal_id = fields.Many2one('account.journal', 'Journal', required=True)
    options = fields.Serialized('Options')

    @api.model
    @tools.ormcache()
    def _get_model_names(self):
        return [
            model for model in self.env.registry
            if self.env[model]._name != auto_reconcile_base._name and
            issubclass(self.env[model].__class__, auto_reconcile_base)
        ]

    @api.model
    def _sel_rule_type(self):
        return self.env['ir.model'].search([
            ('model', 'in', self._get_model_names()),
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

    @api.model
    def create(self, values):
        self._options_from_values(values)
        return super(AccountBankStatementImportAutoReconcileRule, self).create(
            values
        )

    @api.multi
    def write(self, values):
        self._options_from_values(values)
        return super(AccountBankStatementImportAutoReconcileRule, self).write(
            values
        )

    @api.multi
    def read(self, fields=None, load='_classic_read'):
        rule_type_fields = []
        self_fields = []
        for field in fields or []:
            if field in self._fields:
                self_fields.append(field)
            else:
                rule_type_fields.append(field)
        if self_fields and rule_type_fields and 'options' not in self_fields:
            self_fields.append('options')
        result = super(AccountBankStatementImportAutoReconcileRule, self)\
            .read(fields=self_fields or None, load=load)
        if not rule_type_fields:
            return result
        defaults = {}
        for model_name in self._get_model_names():
            defaults.update(self.env[model_name].default_get(rule_type_fields))
        for res in result:
            for field in rule_type_fields:
                res[field] = res['options'].get(field, defaults.get(field))
        return result

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False,
                        submenu=False):
        """Carve a view such that we can inject every field the view of the
        currently selected matching rule into our form"""
        # TODO: at a certain point, we'll have to namespace field names in
        # order to avoid clashes
        result = super(AccountBankStatementImportAutoReconcileRule, self)\
            .fields_view_get(view_id=view_id, view_type=view_type,
                             toolbar=toolbar, submenu=submenu)
        standard_fields = set(self.env[auto_reconcile_base._name]._fields)
        arch = etree.fromstring(result['arch'])
        container = arch.xpath('//div[@name="rule_options"]')[0]

        for model_name in self._get_model_names():
            fields_view = self.env[model_name].fields_view_get()
            if set(fields_view['fields']).issubset(standard_fields):
                # this is an autogenerated form
                continue
            group = etree.SubElement(
                container,
                'div',
                modifiers='{"invisible": [["rule_type", "!=", "%s"]]}' % (
                    model_name,
                )
            )
            form = etree.fromstring(fields_view['arch'])
            for element in form:
                group.append(element)
            for field in group.xpath('descendant::field[@modifiers]'):
                # TODO: merging modifiers would be better
                del field.attrib['modifiers']

            for key, value in fields_view['fields'].iteritems():
                result['fields'][key] = dict(value, readonly=False)

        result['arch'] = etree.tostring(arch)
        return result

    @api.multi
    def name_get(self):
        return [
            (this.id, self.env[this.rule_type]._description)
            for this in self
        ]

    @api.multi
    def _options_from_values(self, values):
        """Write values we got from the user into options dict"""
        if 'options' in values:
            return
        rule = values.get('rule_type', self and self[:1].rule_type or None)
        if not rule or rule not in self.env.registry:
            return
        rule_model = self.env[rule]
        options = self and self[:1].options or {}
        for field_name in rule_model._fields:
            if field_name in values:
                options[field_name] = values.pop(field_name)
        values['options'] = options

    @api.multi
    def get_rules(self):
        """Return a NewId object for the configured rule"""
        rules = self.mapped(
            lambda x: self.env[x.rule_type].new({
                'wizard_id': self.id,
                'options': x.options
            })
            if x else None
        )
        for rule in rules:
            rule.update(rule.options)
        return rules
