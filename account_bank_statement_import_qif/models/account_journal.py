# -*- coding: utf-8 -*-
from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    qif_date_format = fields.Selection([
        ('dmy', 'DD/MM/YYYY'),
        ('mdy', 'MM/DD/YYYY'),
        ('ymd', 'YYYY/MM/DD')], string='QIF Date format', default='dmy')
