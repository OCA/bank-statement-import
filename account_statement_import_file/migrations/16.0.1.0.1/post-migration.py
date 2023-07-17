# Copyright 2023 Landoo Sistemas de Informacion SL
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        """
        UPDATE account_journal
        SET bank_statements_source = 'file_import_oca'
        WHERE bank_statements_source = 'file_import'
        """,
    )
