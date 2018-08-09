# -*- coding: utf-8 -*-
# Copyright 2009-2017 Noviat.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import models
from odoo.addons.base.res.res_bank import sanitize_account_number


class AccountBankStatementImport(models.TransientModel):
    """
    add support for local bank account numbers which are in several
    countries a subset of the IBAN
    """
    _inherit = 'account.bank.statement.import'

    def _find_additional_data(self, currency_code, account_number):
        currency, journal = super(
            AccountBankStatementImport, self
        )._find_additional_data(currency_code, account_number)
        if not journal:
            sanitized_account_number = sanitize_account_number(account_number)
            fin_journals = self.env['account.journal'].search(
                [('type', '=', 'bank')])
            fin_journal = fin_journals.filtered(
                lambda r: sanitized_account_number
                in r.bank_account_id.sanitized_acc_number)
            if len(fin_journal) == 1:
                journal = fin_journal
        return currency, journal

    def _check_journal_bank_account(self, journal, account_number):
        check = super(
            AccountBankStatementImport, self
        )._check_journal_bank_account(journal, account_number)
        if not check:
            check = account_number \
                in journal.bank_account_id.sanitized_acc_number
        return check
