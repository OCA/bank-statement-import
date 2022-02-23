# pylint: disable=C7902
# Copyright 2022 ForgeFlow S.L.  <https://www.forgeflow.com>
# License LGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).
from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    if openupgrade.column_exists(
        env.cr, "account_bank_statement_line", "partner_bank_id"
    ):
        # during v14, a partner_bank_id field was added to statement lines,
        # but later we realized it is not needed.
        # As we remove the explicit partner_bank_id in statement line, we need to transfer the
        # values to the move for getting them through delegated inheritance
        openupgrade.logged_query(
            env.cr,
            """
            UPDATE account_move am
            SET partner_bank_id = absl.partner_bank_id
            FROM account_bank_statement_line absl
            WHERE am.statement_line_id = absl.id
                AND am.partner_bank_id IS NULL AND absl.partner_bank_id IS NOT NULL""",
        )
        openupgrade.lift_constraints(
            env.cr, "account_bank_statement_line", "partner_bank_id"
        )
