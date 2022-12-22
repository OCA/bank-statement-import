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


def amount_to_debit_amount_and_amount2_to_credit_amount(env):
    cr = env.cr
    sql_amount2_exists = """SELECT count(id) FROM ir_model_fields
        WHERE name = 'amount2_column'
        AND model = 'account.statement.import.sheet.mapping';"""
    cr.execute(sql_amount2_exists)
    if cr.fetchone()[0] > 0:
        openupgrade.add_fields(env, _fields_to_add)
        cr.execute(
            """ALTER TABLE account_statement_import_sheet_mapping
            ALTER COLUMN amount_column DROP NOT NULL;"""
        )
        openupgrade.logged_query(
            cr,
            """
                UPDATE account_statement_import_sheet_mapping
                SET
                    amount_credit_column = amount2_column,
                    amount_debit_column = amount_column,
                    amount_column = NULL
                WHERE amount2_column IS NOT NULL;
            """,
        )


@openupgrade.migrate()
def migrate(env, version):
    amount_to_debit_amount_and_amount2_to_credit_amount(env)
