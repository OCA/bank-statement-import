# Copyright 2025 Nitrokey GmbH
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).

from openupgradelib import openupgrade


def migrate(cr, version):
    """
    Pre-migration script to handle field renaming from transferwise to wise.
    """
    # Rename field transferwise_profile to wise_profile
    if openupgrade.column_exists(
        cr, "online_bank_statement_provider", "transferwise_profile"
    ):
        openupgrade.rename_fields(
            cr,
            [
                (
                    "online.bank.statement.provider",
                    "online_bank_statement_provider",
                    "transferwise_profile",
                    "wise_profile",
                ),
            ],
        )

    # Update service field values from 'transferwise' to 'wise'
    openupgrade.logged_query(
        cr,
        """
        UPDATE online_bank_statement_provider
        SET service = 'wise'
        WHERE service = 'transferwise'
        """,
    )
