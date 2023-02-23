# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade

_column_renames = {
    "account_bank_statement_line": [
        ("online_raw_data", None),
    ]
}


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.column_exists(
        env.cr, "account_bank_statement_line", "online_raw_data"
    ):
        openupgrade.rename_columns(env.cr, _column_renames)
