# Copyright 2021 Tecnativa - Carlos Roca
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_model_renames = [
    (
        "account.bank.statement.import.sheet.mapping",
        "account.statement.import.sheet.mapping",
    ),
    (
        "account.bank.statement.import.sheet.parser",
        "account.statement.import.sheet.parser",
    ),
    (
        "account.bank.statement.import.sheet.mapping.wizard",
        "account.statement.import.sheet.mapping.wizard",
    ),
]

_table_renames = [
    (
        "account_bank_statement_import_sheet_mapping",
        "account_statement_import_sheet_mapping",
    ),
    (
        "account_bank_statement_import_sheet_parser",
        "account_statement_import_sheet_parser",
    ),
    (
        "account_bank_statement_import_sheet_mapping_wizard",
        "account_statement_import_sheet_mapping_wizard",
    ),
]


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.rename_models(env.cr, _model_renames)
    openupgrade.rename_tables(env.cr, _table_renames)
