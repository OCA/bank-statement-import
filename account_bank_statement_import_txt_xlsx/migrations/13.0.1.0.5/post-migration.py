# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
UPDATE account_bank_statement_import_sheet_mapping
    SET amount_type = 'absolute_value'
    WHERE debit_credit_column IS NOT NULL;
       """,
    )
