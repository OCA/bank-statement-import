# Copyright 2022 Akretion France (http://www.akretion.com/)
# @author: Alexis de Lattre <alexis.delattre@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.logged_query(
        env.cr,
        "UPDATE account_bank_statement_line SET raw_data={online_raw_data}".format(
            online_raw_data=openupgrade.get_legacy_name("online_raw_data")
        ),
    )
