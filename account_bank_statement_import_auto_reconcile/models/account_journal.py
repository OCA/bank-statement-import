# -*- coding: utf-8 -*-
# Copyright 2017 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    statement_import_auto_reconcile_rule_ids = fields.One2many(
        'account.bank.statement.import.auto.reconcile.rule',
        'journal_id', string='Automatic reconciliation rules',
        help='When importing a bank statement into this journal ,'
        'apply the following rules for automatic reconciliation',
    )
