# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_model_renames = [
    (
        "account.bank.statement.import.paypal.mapping",
        "account.statement.import.paypal.mapping",
    ),
    (
        "account.bank.statement.import.paypal.parser",
        "account.statement.import.paypal.parser",
    ),
    (
        "account.bank.statement.import.paypal.mapping.wizard",
        "account.statement.import.paypal.mapping.wizard",
    ),
]

_table_renames = [
    (
        "account_bank_statement_import_paypal_mapping",
        "account_statement_import_paypal_mapping",
    ),
    (
        "account_bank_statement_import_paypal_parser",
        "account_statement_import_paypal_parser",
    ),
    (
        "account_bank_statement_import_paypal_mapping_wizard",
        "account_statement_import_paypal_mapping_wizard",
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _model_renames)
    openupgrade.rename_tables(env.cr, _table_renames)
