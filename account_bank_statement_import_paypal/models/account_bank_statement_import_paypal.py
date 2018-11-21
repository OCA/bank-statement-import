# Copyright 2014-2017 Akretion (http://www.akretion.com).
# @author Alexis de Lattre <alexis.delattre@akretion.com>
# @author Sébastien BEAU <sebastien.beau@akretion.com>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
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

# Paypal header depend of the country the order are the same but the
# value are translated. You can add you header here

HEADERS = [
    # French
    '"Date","Heure","Fuseau horaire","Description","Devise","Avant commission"'
    ',"Commission","Net","Solde","Numéro de transaction","Adresse email de '
    'l\'expéditeur","Nom","Nom de la banque","Compte bancaire","Montant des '
    'frais de livraison et de traitement","TVA","Identifiant de facture",'
    '"Numéro de la transaction de référence"',
    # English
    '"Date","Time","Time Zone","Description","Currency","Gross ","Fee ","Net",'
    '"Balance","Transaction ID","From Email Address","Name","Bank Name",'
    '"Bank Account","Shipping and Handling Amount","Sales Tax","Invoice ID",'
    '"Reference Txn ID"',
    ]


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _get_paypal_encoding(self):
        return 'utf-8-sig'

    @api.model
    def _get_paypal_str_data(self, data_file):
        if not isinstance(data_file, str):
            data_file = data_file.decode(self._get_paypal_encoding())
        return data_file.strip()

    @api.model
    def _get_paypal_date_format(self):
        """ This method is designed to be inherited """
        return '%d/%m/%Y'

    @api.model
    def _paypal_convert_amount(self, amount_str):
        """ This method is designed to be inherited """
        valstr = re.sub(r'[^\d,.-]', '', amount_str)
        valstrdot = valstr.replace('.', '')
        valstrdot = valstrdot.replace(',', '.')
        return float(valstrdot)

    @api.model
    def _check_paypal(self, data_file):
        data_file = self._get_paypal_str_data(data_file)
        for header in HEADERS:
            if data_file.strip().startswith(header):
                return True
        return False

    def _convert_paypal_line_to_dict(self, idx, line):
        date_dt = datetime.strptime(line[0], self._get_paypal_date_format())
        rline = {
            'date': fields.Date.to_string(date_dt),
            'time': line[1],
            'description': line[3],
            'currency': line[4],
            'amount': line[5],
            'commission': line[6],
            'balance': line[8],
            'transaction_id': line[9],
            'email': line[10],
            'partner_name': line[11],
            # This two field are useful for bank transfer
            'bank_name': line[12],
            'bank_account': line[13],
            'invoice_number': line[16],
            'origin_transaction_id': line[17],
            'idx': idx,
        }
        for field in ['commission', 'amount', 'balance']:
            _logger.debug('Trying to convert %s to float' % rline[field])
            try:
                rline[field] = self._paypal_convert_amount(rline[field])
            except Exception:
                raise UserError(
                    _("Value '%s' for the field '%s' on line %d, "
                        "cannot be converted to float")
                    % (rline[field], field, idx))
        return rline

    def _parse_paypal_file(self, data_file):
        data_file = self._get_paypal_str_data(data_file)
        f = StringIO(data_file)
        f.seek(0)
        raw_lines = []
        reader = csv.reader(f)
        next(reader)  # Drop header
        for idx, line in enumerate(reader):
            _logger.debug("Line %d: %s" % (idx, line))
            raw_lines.append(self._convert_paypal_line_to_dict(idx, line))
        return raw_lines

    def _prepare_paypal_currency_vals(self, cline):
        currencies = self.env['res.currency'].search(
            [('name', '=', cline['currency'])])
        if not currencies:
            raise UserError(
                _('currency %s on line %d cannot be found in odoo')
                % (cline['currency'], cline['idx']))
        return {
            'amount_currency': cline['amount'],
            'currency_id': currencies.id,
            'currency': cline['currency'],
            'partner_name': cline['partner_name'],
            'description': cline['description'],
            'email': cline['email'],
            'transaction_id': cline['transaction_id'],
            }

    def _post_process_statement_line(self, raw_lines):
        journal_id = self.env.context.get('journal_id')
        if not journal_id:
            raise UserError(_('You must run this wizard from the journal'))
        journal = self.env['account.journal'].browse(journal_id)
        currency = journal.currency_id or journal.company_id.currency_id
        currency_change_lines = {}
        real_transactions = []
        for line in raw_lines:
            if line['currency'] != currency.name:
                currency_change_lines[line['transaction_id']] = line
            else:
                real_transactions.append(line)

        for line in real_transactions:
            # Check if the current transaction is linked with a
            # transaction of currency change if yes merge the transaction
            # as for odoo it's only one line
            cline = currency_change_lines.get(line['origin_transaction_id'])
            if cline:
                # we update the current line with currency information
                vals = self._prepare_paypal_currency_vals(cline)
                line.update(vals)
        return real_transactions

    def _prepare_paypal_statement_line(self, fline):
        if fline['bank_name']:
            name = '|'.join([
                fline['description'],
                fline['bank_name'],
                fline['bank_account']
                ])
        else:
            name = '|'.join([
                fline['description'],
                fline['partner_name'],
                fline['email'],
                fline['invoice_number'],
                ])
        return {
            'date': fline['date'],
            'name': name,
            'ref': fline['transaction_id'],
            'unique_import_id':
                fline['transaction_id'] + fline['date'] + fline['time'],
            'amount': fline['amount'],
            'bank_account_id': False,
            'currency_id': fline.get('currency_id'),
            'amount_currency': fline.get('amount_currency'),
            }

    def _prepare_paypal_statement(self, lines):
        return {
            'name':
                _('PayPal Import %s > %s')
                % (lines[0]['date'], lines[-1]['date']),
            'date': lines[-1]['date'],
            'balance_start':
                lines[0]['balance'] -
                lines[0]['amount'] -
                lines[0]['commission'],
            'balance_end_real': lines[-1]['balance'],
            }

    @api.model
    def _parse_file(self, data_file):
        """ Import a file in Paypal CSV format """
        paypal = self._check_paypal(data_file)
        if not paypal:
            return super(AccountBankStatementImport, self)._parse_file(
                data_file)

        raw_lines = self._parse_paypal_file(data_file)
        final_lines = self._post_process_statement_line(raw_lines)

        vals_bank_statement = self._prepare_paypal_statement(final_lines)

        transactions = []
        commission_total = 0
        for fline in final_lines:
            commission_total += fline['commission']
            vals_line = self._prepare_paypal_statement_line(fline)
            _logger.debug("vals_line = %s" % vals_line)
            transactions.append(vals_line)

        if commission_total:
            commission_line = {
                'date': vals_bank_statement['date'],
                'name': _('Paypal commissions'),
                'ref': _('PAYPAL-COSTS'),
                'amount': commission_total,
                'unique_import_id': False,
                }
            transactions.append(commission_line)

        vals_bank_statement['transactions'] = transactions
        return None, None, [vals_bank_statement]

    @api.model
    def _get_paypal_partner(self, description, partner_name,
                            partner_email, invoice_number):
        if invoice_number:
            # In most case e-commerce case invoice_number
            # will contain the sale order number
            sale = self.env['sale.order'].search([
                ('name', '=', invoice_number)])
            if sale and len(sale) == 1:
                return sale.partner_id.commercial_partner_id

            invoice = self.env['account.invoice'].search([
                ('number', '=', invoice_number)])
            if invoice and len(invoice) == 1:
                return invoice.partner_id.commercial_partner_id

        if partner_email:
            partner = self.env['res.partner'].search([
                ('email', '=', partner_email),
                ('parent_id', '=', False)])
            if partner and len(partner) == 1:
                return partner.commercial_partner_id

        if partner_name:
            partner = self.env['res.partner'].search([
                ('name', '=ilike', partner_name)])
            if partner and len(partner) == 1:
                return partner.commercial_partner_id
        return None

    @api.model
    def _complete_paypal_statement_line(self, line):
        _logger.debug('Process line %s', line['name'])
        info = line['name'].split('|')
        if len(info) == 4:
            partner = self._get_paypal_partner(*info)
            if partner:
                return {
                    'partner_id': partner.id,
                    'account_id': partner.property_account_receivable.id,
                    }
        return None

    @api.model
    def _complete_statement(self, stmts_vals, journal_id, account_number):
        """ Match the partner from paypal information """
        stmts_vals = super(AccountBankStatementImport, self).\
            _complete_statement(stmts_vals, journal_id, account_number)
        for line in stmts_vals['transactions']:
            vals = self._complete_paypal_statement_line(line)
            if vals:
                line.update(vals)
        return stmts_vals
