# Copyright 2023 Tecnativa - Pedro M. Baeza
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    # Remove record that has changed its based model
    env.ref(
        "account_statement_import_online.action_online_bank_statements_pull_wizard"
    ).unlink()
