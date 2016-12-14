# -*- coding: utf-8 -*-
# Copyright 2009-2016 Noviat
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from openerp import models, fields


class account_journal(models.Model):
    _inherit = 'account.journal'

    enforce_sequence = fields.Boolean(
        string="Enforce Sequence",
        help="If checked, the Journal Sequence will determine "
             "the statement naming policy even if the name is already "
             "set manually or by the statement import software.")
