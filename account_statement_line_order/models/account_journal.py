# Copyright 2025 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    statement_line_internal_index = fields.Selection(
        [
            ("date_line_sequence_id", "Default (Date, Line sequence/ID)"),
            (
                "date_statement_id_line_sequence_id",
                "Statement together (Date, Statement ID, Line sequence/ID)",
            ),
        ],
        default="date_line_sequence_id",
        help="Allow to select the computing method for the order sequence "
        "of the bank statement lines.",
    )
