# -*- coding: utf-8 -*-
# Copyright 2013-2016 Therp BV <http://therp.nl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openerp import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    camt_import_batch = fields.Boolean(
        string='Aggregate batch transactions (CAMT)')
