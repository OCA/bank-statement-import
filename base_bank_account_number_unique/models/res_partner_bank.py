# -*- coding: utf-8 -*-
# Copyright 2015-2018 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openerp import api, models, _
from openerp.exceptions import ValidationError


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    @api.multi
    def copy_data(self, default=None):
        default = default or {}
        if 'acc_number' not in default and \
                'default_acc_number' not in self.env.context:
            default['acc_number'] = ''
        return super(ResPartnerBank, self).copy_data(default=default)

    @api.constrains('company_id', 'sanitized_acc_number')
    def _check_unique_account(self):
        for this in self:
            check_domain = [
                ('sanitized_acc_number', '=', this.sanitized_acc_number),
            ]
            # No problem if one record has a company and the other not:
            if this.company_id:
                check_domain.append(('company_id', '=', this.company_id.id))
            else:
                check_domain.append(('company_id', '=', False))
            # Do not find same record, if existing:
            if this.exists():
                check_domain.append(('id', '<>', this.id))
            already_existing = self.search(check_domain)
            if already_existing:
                raise ValidationError(
                    _("Bank account %s already registered for %s.") %
                    (this.acc_number,
                     already_existing.partner_id.display_name or
                     _("unknown partner"))
                )
