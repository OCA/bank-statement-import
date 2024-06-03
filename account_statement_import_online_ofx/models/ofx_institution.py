# Copyright 2023 ForgeFlow S.L.
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).


from odoo import fields, models


class OFXInstitution(models.Model):
    _name = "ofx.institution"
    _description = "OFX Institution"

    name = fields.Char()
    nickname = fields.Char()
    ofxhome_id = fields.Integer()
