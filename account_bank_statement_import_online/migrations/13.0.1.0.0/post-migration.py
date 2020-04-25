# Copyright 2020 Brainbean Apps (https://brainbeanapps.com)
# Copyright 2020 Dataplug (https://dataplug.io)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from openupgradelib import openupgrade  # pylint: disable=W7936


@openupgrade.migrate()
def migrate(env, version):
    openupgrade.load_data(
        env.cr,
        "account_bank_statement_import_online",
        "migrations/13.0.1.0.0/noupdate_changes.xml",
    )
