# Copyright 2022 AppsToGROW - Henrik Norlin
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_fields_to_add = [
    (
        "amount_debit_column",
        "account.statement.import.sheet.mapping",
        "account_statement_import_sheet_mapping",
        "char",
        "varchar",
        "account_statement_import_txt_xlsx",
    ),
    (
        "amount_credit_column",
        "account.statement.import.sheet.mapping",
        "account_statement_import_sheet_mapping",
        "char",
        "varchar",
        "account_statement_import_txt_xlsx",
    ),
]


def add_fields_and_drop_not_null(env):
    cr = env.cr
    sql_debit_exists = """SELECT count(id) FROM ir_model_fields
        WHERE name = 'amount_debit_column'
        AND model = 'account.statement.import.sheet.mapping';"""
    cr.execute(sql_debit_exists)
    if cr.fetchone()[0] > 0:
        openupgrade.add_fields(env, _fields_to_add)
        cr.execute(
            """ALTER TABLE account_statement_import_sheet_mapping
            ALTER COLUMN amount_column DROP NOT NULL;"""
        )


@openupgrade.migrate()
def migrate(env, version):
    add_fields_and_drop_not_null(env)
