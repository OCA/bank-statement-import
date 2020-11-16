# -*- coding: utf-8 -*-
# Copyright 2004-2020 Odoo S.A.
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).

from odoo import api, fields, models


class AccountBankStatementImportJounalCreation(models.TransientModel):
    _name = 'account.bank.statement.import.journal.creation'
    _description = 'Journal Creation on Bank Statement Import'

    journal_id = fields.Many2one('account.journal', delegate=True, required=True, ondelete='cascade')

    def create_journal(self):
        """ Create the journal (the record is automatically created in the process of calling this method) and reprocess the statement """
        statement_import_transient = self.env['account.bank.statement.import'].browse(self.env.context['statement_import_transient_id'])
        return statement_import_transient.with_context(journal_id=self.journal_id.id).import_file()
