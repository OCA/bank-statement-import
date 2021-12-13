# Copyright 2021 Therp BV <https://therp.nl>.
# @author: Ronald Portier <ronald@therp.nl>.
# Licence LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl-3.0).
"""Add raw data to statement line, to solve import issues."""

from odoo import fields, models


class AccountBankStatementLine(models.Model):
    """Add raw data to statement line, to solve import issues."""

    _inherit = "account.bank.statement.line"

    online_raw_data = fields.Text(
        help="The complete data retrieved online for this transaction",
        readonly=True,
        copy=False,
    )
