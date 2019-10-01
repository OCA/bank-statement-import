# Copyright 2014-2017 Akretion (http://www.akretion.com).
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# Copyright 2019 Eficent Business and IT Consulting Services, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import xlrd
import logging
import datetime as dtm
from datetime import datetime
from odoo import _, api, fields, models
from odoo.exceptions import UserError
import re
from io import StringIO
_logger = logging.getLogger(__name__)

try:
    import csv
except (ImportError, IOError) as err:
    _logger.debug(err)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    txt_map_id = fields.Many2one(
        comodel_name='account.bank.statement.import.map',
        string='Txt map',
        readonly=True,
    )

    @api.model
    def _get_txt_encoding(self):
        if self.txt_map_id.file_encoding:
            return self.txt_map_id.file_encoding
        return 'utf-8-sig'

    @api.model
    def _get_txt_str_data(self, data_file):
        if not isinstance(data_file, str):
            data_file = data_file.decode(self._get_txt_encoding())
        return data_file.strip()

    @api.model
    def _txt_convert_amount(self, amount_str):
        if not amount_str:
            return 0.0
        if self.txt_map_id:
            thousands, decimal = self.txt_map_id._get_separators()
        else:
            thousands, decimal = ',', '.'
        valstr = re.sub(r'[^\d%s%s.-]' % (thousands, decimal), '', amount_str)
        valstrdot = valstr.replace(thousands, '')
        valstrdot = valstrdot.replace(decimal, '.')
        return float(valstrdot)

    @api.model
    def _check_xls(self, data_file):
        # Try if it is an Excel file
        headers = self.mapped('txt_map_id.map_line_ids.name')
        try:
            file_headers = []
            book = xlrd.open_workbook(file_contents=data_file)
            xl_sheet = book.sheet_by_index(0)
            row = xl_sheet.row(0)  # 1st row
            for idx, cell_obj in enumerate(row):
                cell_type_str = xlrd.sheet.ctype_text.get(cell_obj.ctype, False)
                if cell_type_str:
                    file_headers.append(cell_obj.value)
                else:
                    return False
            if any(item not in file_headers for item in headers):
                raise UserError(
                    _("Headers of file to import and Txt map lines does not "
                      "match."))
        except xlrd.XLRDError as e:
            return False
        except Exception as e:
            return False
        return True

    @api.model
    def _check_txt(self, data_file):
        data_file = self._get_txt_str_data(data_file)
        if not self.txt_map_id:
            return False
        headers = self.mapped('txt_map_id.map_line_ids.name')
        file_headers = data_file.split('\n', 1)[0]
        if any(item not in file_headers for item in headers):
            raise UserError(
                _("Headers of file to import and Txt map lines does not "
                  "match."))
        return True

    def _get_currency_fields(self):
        return ['amount', 'amount_currency']

    def _convert_txt_line_to_dict(self, idx, line):
        rline = dict()
        for item in range(len(line)):
            txt_map = self.mapped('txt_map_id.map_line_ids')[item]
            value = line[item]
            if not txt_map.field_to_assign:
                continue
            if txt_map.date_format:
                try:
                    value = fields.Date.to_string(
                        datetime.strptime(value, txt_map.date_format))
                except Exception:
                    raise UserError(
                        _("Date format of map file and Txt date does "
                          "not match."))
            rline[txt_map.field_to_assign] = value
        for field in self._get_currency_fields():
            _logger.debug('Trying to convert %s to float' % rline[field])
            try:
                rline[field] = self._txt_convert_amount(rline[field])
            except Exception:
                raise UserError(
                    _("Value '%s' for the field '%s' on line %d, "
                        "cannot be converted to float")
                    % (rline[field], field, idx))
        return rline

    def _parse_txt_file(self, data_file):
        data_file = self._get_txt_str_data(data_file)
        f = StringIO(data_file)
        f.seek(0)
        raw_lines = []
        if not self.txt_map_id.quotechar:
            reader = csv.reader(f,
                                delimiter=self.txt_map_id.delimiter or False)
        else:
            reader = csv.reader(f,
                                quotechar=self.txt_map_id.quotechar,
                                delimiter=self.txt_map_id.delimiter or False)
        next(reader)  # Drop header
        for idx, line in enumerate(reader):
            _logger.debug("Line %d: %s" % (idx, line))
            raw_lines.append(self._convert_txt_line_to_dict(idx, line))
        return raw_lines

    def _convert_xls_line_to_dict(self, row_idx, xl_sheet):
        rline = dict()
        for col_idx in range(0, xl_sheet.ncols):  # Iterate through columns
            txt_map = self.mapped('txt_map_id.map_line_ids')[col_idx]
            cell_obj = xl_sheet.cell(row_idx, col_idx)  # Get cell
            ctype = xl_sheet.cell(row_idx, col_idx).ctype
            value = cell_obj.value
            if not txt_map.field_to_assign:
                continue
            if ctype == xlrd.XL_CELL_DATE:
                ms_date_number = xl_sheet.cell(row_idx, col_idx).value
                try:
                    year, month, day, hour, minute, \
                        second = xlrd.xldate_as_tuple(
                            ms_date_number, 0)
                except xlrd.XLDateError as e:
                    raise UserError(
                        _('An error was found translating a date '
                          'field from the file: %s') % e)
                value = dtm.date(year, month, day)
                value = value.strftime('%Y-%m-%d')
            rline[txt_map.field_to_assign] = value

        return rline

    def _parse_xls_file(self, data_file):
        try:
            raw_lines = []
            book = xlrd.open_workbook(file_contents=data_file)
            xl_sheet = book.sheet_by_index(0)
            for row_idx in range(1, xl_sheet.nrows):
                _logger.debug("Line %d" % row_idx)
                raw_lines.append(self._convert_xls_line_to_dict(
                    row_idx, xl_sheet))
        except xlrd.XLRDError:
            return False
        except Exception as e:
            return False
        return raw_lines

    def _post_process_statement_line(self, raw_lines):
        """ Enter your additional logic here. """
        return raw_lines

    def _get_journal(self):
        journal_id = self.env.context.get('journal_id')
        if not journal_id:
            raise UserError(_('You must run this wizard from the journal'))
        return self.env['account.journal'].browse(journal_id)

    def _get_currency_id(self, fline):
        journal = self._get_journal()
        line_currency_name = fline.get('currency', False)
        currency = journal.currency_id or journal.company_id.currency_id
        if line_currency_name and line_currency_name != currency.name:
            currency = self.env['res.currency'].search(
                [('name', '=', fline['currency'])], limit=1)
            return currency.id
        return False

    @api.model
    def _get_partner_id(self, fline):
        partner_name = fline.get('partner_name', False)
        if partner_name:
            partner = self.env['res.partner'].search([
                ('name', '=ilike', partner_name)])
            if partner and len(partner) == 1:
                return partner.commercial_partner_id.id
        return None

    def _prepare_txt_statement_line(self, fline):
        currency_id = self._get_currency_id(fline)
        return {
            'date': fline.get('date', False),
            'name': fline.get('name', ''),
            'ref': fline.get('ref', False),
            'note': fline.get('Notes', False),
            'amount': fline.get('amount', 0.0),
            'currency_id': self._get_currency_id(fline),
            'amount_currency': currency_id and fline.get(
                'amount_currency', 0.0) or 0.0,
            'partner_id': self._get_partner_id(fline),
            'account_number': fline.get('account_number', False),
            }

    def _prepare_txt_statement(self, lines):
        balance_end_real = 0.0
        for line in lines:
            if 'amount' in line and line['amount']:
                balance_end_real += line['amount']

        return {
            'name':
                _('%s Import %s > %s')
                % (self.txt_map_id.name,
                   lines[0]['date'], lines[-1]['date']),
            'date': lines[-1]['date'],
            'balance_start': 0.0,
            'balance_end_real': balance_end_real,
            }

    @api.model
    def _parse_file(self, data_file):
        """ Import a file in Txt CSV format """
        is_txt = False
        is_xls = self._check_xls(data_file)
        if not is_xls:
            is_txt = self._check_txt(data_file)
        if not is_txt and not is_xls:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)
        if is_txt:
            raw_lines = self._parse_txt_file(data_file)
        else:
            raw_lines = self._parse_xls_file(data_file)
        final_lines = self._post_process_statement_line(raw_lines)
        vals_bank_statement = self._prepare_txt_statement(final_lines)
        transactions = []
        for fline in final_lines:
            vals_line = self._prepare_txt_statement_line(fline)
            _logger.debug("vals_line = %s" % vals_line)
            transactions.append(vals_line)
        vals_bank_statement['transactions'] = transactions
        return None, None, [vals_bank_statement]

    @api.model
    def _complete_txt_statement_line(self, line):
        """ Enter additional logic here. """
        return None

    @api.model
    def _complete_stmts_vals(self, stmts_vals, journal_id, account_number):
        stmts_vals = super(AccountBankStatementImport, self). \
            _complete_stmts_vals(stmts_vals, journal_id, account_number)
        for line in stmts_vals[0]['transactions']:
            vals = self._complete_txt_statement_line(line)
            if vals:
                line.update(vals)
        return stmts_vals

    @api.model
    def default_get(self, fields):
        res = super(AccountBankStatementImport, self).default_get(fields)
        journal = self._get_journal()
        res['txt_map_id'] = journal.statement_import_txt_map_id.id
        return res
