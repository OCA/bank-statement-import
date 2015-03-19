# -*- coding: utf-8 -*-
##############################################################################
#
#     This file is part of account_bank_statement_import_coda,
#     an Odoo module.
#
#     Copyright (c) 2015 ACSONE SA/NV (<http://acsone.eu>)
#
#     account_bank_statement_import_coda is free software:
#     you can redistribute it and/or modify it under the terms of the GNU
#     Affero General Public License as published by the Free Software
#     Foundation,either version 3 of the License, or (at your option) any
#     later version.
#
#     account_bank_statement_import_coda is distributed
#     in the hope that it will be useful, but WITHOUT ANY WARRANTY; without
#     even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
#     PURPOSE.  See the GNU Affero General Public License for more details.
#
#     You should have received a copy of the GNU Affero General Public License
#     along with account_bank_statement_import_coda.
#     If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import zipfile
import logging
from cStringIO import StringIO

from openerp import api, models
from openerp.tools.translate import _
from openerp.exceptions import ValidationError
from openerp.loglevels import ustr

_logger = logging.getLogger(__name__)


class account_bank_statement_import(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    def _get_error_notification(self, file_name,  exc):
        return [{
            'type': 'error',
            'message': _('Import of %s failed with error %s'
                         ) % (ustr(file_name),
                              ustr(exc)),
            }]

    @api.model
    def _import_file(self, data_file):
        file_buffer = StringIO(data_file)
        if not zipfile.is_zipfile(file_buffer):
            return super(account_bank_statement_import, self)._import_file(
                data_file)
        errors = []
        statement_ids = []
        notifications = []
        file_buffer.seek(0)
        try:
            with zipfile.ZipFile(file_buffer, mode="r") as myzip:
                for name in myzip.namelist():
                    _logger.debug('Reading file %s from archive', ustr(name))
                    single_data = myzip.read(name)
                    try:
                        st_ids, notes = self._import_file(single_data)
                        statement_ids.extend(st_ids)
                        notifications.extend(notes)
                    except Exception as e:
                        _logger.exception('Import of %s failed', name)
                        errors.append(self._get_error_notification(name, e))
            if errors:
                notifications.extend(errors)
        except Exception:
            _logger.exception('Error reading zipfile')
            raise ValidationError(_("File seems to be an invalid zip file"))
        return statement_ids, notifications
