# Copyright 2019 Tecnativa - Vicent Cubells
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import csv
import base64
from odoo import api, fields, models
from io import StringIO


class WizardPaypalMapCreate(models.TransientModel):
    _name = 'wizard.paypal.map.create'

    data_file = fields.Binary(
        string='Bank Statement File',
        required=True,
    )
    filename = fields.Char()

    @api.multi
    def create_map_lines(self):
        statement_obj = self.env['account.bank.statement.import.paypal.map']
        data_file = base64.b64decode(self.data_file)
        if not isinstance(data_file, str):
            data_file = data_file.decode('utf-8-sig').strip()
        file = StringIO(data_file)
        file.seek(0)
        reader = csv.reader(file)
        headers = []
        for row in reader:
            headers = row
            break
        lines = []
        for idx, title in enumerate(headers):
            lines.append((0, 0, {'sequence': idx, 'name': title}))
        if lines:
            for statement in statement_obj.browse(
                    self.env.context.get('active_ids')):
                statement.map_line_ids = lines
