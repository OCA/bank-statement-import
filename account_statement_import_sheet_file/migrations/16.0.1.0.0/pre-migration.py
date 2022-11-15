# Copyright 2023 Tecnativa - Víctor Martínez
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Add amount_type column and set values to keep the same functionality as in v15
    if not openupgrade.column_exists(
        env.cr, "account_statement_import_sheet_mapping", "amount_type"
    ):
        openupgrade.logged_query(
            env.cr,
            """
            ALTER TABLE account_statement_import_sheet_mapping
            ADD COLUMN IF NOT EXISTS amount_type VARCHAR;
            """,
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_statement_import_sheet_mapping
            SET amount_type = 'simple_value'
            WHERE amount_column IS NOT NULL
            """,
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_statement_import_sheet_mapping
            SET amount_type = 'distinct_credit_debit'
            WHERE amount_debit_column != amount_credit_column
            AND amount_debit_column IS NOT NULL
            AND amount_credit_column IS NOT NULL
            """,
        )
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_statement_import_sheet_mapping
            SET amount_type = 'absolute_value'
            WHERE debit_credit_column IS NOT NULL
            """,
        )
