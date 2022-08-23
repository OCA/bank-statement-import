# Copyright 2020 Akretion
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
UPDATE account_bank_statement_import_sheet_mapping
    SET header_lines_count = 1,
    footer_lines_count = 0,
    column_names_line = 1;
       """
    )

    openupgrade.logged_query(
        env.cr,
        """
UPDATE account_bank_statement_import_sheet_mapping
    SET amount_type = 'absolute_value'
    WHERE debit_credit_column IS NOT NULL;
       """
    )

    openupgrade.logged_query(
        env.cr,
        """
UPDATE account_bank_statement_import_sheet_mapping
    SET amount_type = 'simple_value'
    WHERE debit_credit_column IS NULL;
       """
    )
