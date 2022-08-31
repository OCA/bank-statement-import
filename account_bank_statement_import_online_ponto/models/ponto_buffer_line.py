# Copyright 2022 Therp BV <https://therp.nl>.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl).
"""Define model to hold transactions retrieved from Ponto."""
from odoo import fields, models


class PontoBuffer(models.Model):
    """Define model to hold transactions retrieved from Ponto."""
    _name = "ponto.buffer.line"
    _description = "Hold transactions retrieved from Ponto."

    buffer_id = fields.Many2one(
        comodel_name="ponto.buffer",
        required=True,
        readonly=True,
    )
    ponto_id = fields.Char(
        required=True,
        readonly=True,
    )
    effective_date_time = fields.Datetime(
        required=True,
        readonly=True,
    )
    transaction_data = fields.Char(
        required=True,
        readonly=True,
    )
