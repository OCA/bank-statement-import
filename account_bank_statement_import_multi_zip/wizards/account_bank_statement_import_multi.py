# Copyright 2020 ACSONE SA/NV
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import base64
from io import BytesIO
from zipfile import ZipFile, BadZipFile
from odoo import api, models


class AccountBankStatementImportMulti(models.TransientModel):

    _inherit = 'account.bank.statement.import.multi'

    @api.multi
    def _get_files(self):
        self.ensure_one()
        try:
            with ZipFile(BytesIO(base64.b64decode(self.data_file)), 'r') as \
                    archive:
                for name in archive.namelist():
                    if not name.endswith('/'):
                        yield archive.read(name)
        except BadZipFile:
            return super()._get_files()
