# -*- coding: utf-8 -*-
# Copyright 2017 Therp BV <https://therp.nl>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
{
    "name": "Automatic reconciliation after import",
    "version": "10.0.1.0.0",
    "author": "Therp BV,Odoo Community Association (OCA)",
    "license": "AGPL-3",
    "category": 'Banking addons',
    "summary": "This module allows you to define automatic "
    "reconciliation rules to be run after a bank statement is imported",
    "depends": [
        'account_bank_statement_import',
        'base_domain_operator',
    ],
    "demo": [
        "demo/account_bank_statement_import_auto_reconcile_rule.xml",
    ],
    "data": [
        "views/account_bank_statement_import_reapply_rules.xml",
        "views/account_bank_statement.xml",
        "views/account_bank_statement_import_auto_reconcile_exact_amount.xml",
        "views/account_bank_statement_import.xml",
        "views/account_journal.xml",
        "views/account_bank_statement_import_auto_reconcile_rule.xml",
        'security/ir.model.access.csv',
    ],
}
