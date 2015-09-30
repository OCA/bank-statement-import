# -*- coding: utf-8 -*-
"""Framework for importing bank statement files."""
import logging
import base64

from openerp import api, models, fields
from openerp.tools.translate import _
from openerp.exceptions import Warning

_logger = logging.getLogger(__name__)


class AccountBankStatementLine(models.Model):
    """Extend model account.bank.statement.line."""
    _inherit = "account.bank.statement.line"

    # Ensure transactions can be imported only once (if the import format
    # provides unique transaction ids)
    unique_import_id = fields.Char('Import ID', readonly=True, copy=False)

    _sql_constraints = [
        ('unique_import_id',
         'unique (unique_import_id)',
         'A bank account transactions can be imported only once !')
    ]


class AccountBankStatementImport(models.TransientModel):
    """Extend model account.bank.statement."""
    _name = 'account.bank.statement.import'
    _description = 'Import Bank Statement'

    @api.model
    def _get_hide_journal_field(self):
        """ Return False if the journal_id can't be provided by the parsed
        file and must be provided by the wizard.
        See account_bank_statement_import_qif """
        return True

    journal_id = fields.Many2one(
        'account.journal', string='Journal',
        help='Accounting journal related to the bank statement you\'re '
        'importing. It has be be manually chosen for statement formats which '
        'doesn\'t allow automatic journal detection (QIF for example).')
    hide_journal_field = fields.Boolean(
        string='Hide the journal field in the view',
        compute='_get_hide_journal_field')
    data_file = fields.Binary(
        'Bank Statement File', required=True,
        help='Get you bank statements in electronic format from your bank '
        'and select them here.')

    @api.multi
    def import_file(self):
        """ Process the file chosen in the wizard, create bank statement(s) and
        go to reconciliation."""
        self.ensure_one()
        data_file = base64.b64decode(self.data_file)
        statement_ids, notifications = self.with_context(
            active_id=self.id)._import_file(data_file)
        # dispatch to reconciliation interface
        action = self.env.ref(
            'account.action_bank_reconcile_bank_statements')
        return {
            'name': action.name,
            'tag': action.tag,
            'context': {
                'statement_ids': statement_ids,
                'notifications': notifications
            },
            'type': 'ir.actions.client',
        }

    @api.model
    def _import_file(self, data_file):
        """ Create bank statement(s) from file."""
        # The appropriate implementation module returns the required data
        statement_ids = []
        notifications = []
        parse_result = self._parse_file(data_file)
        # Check for old version result, with separate currency and account
        if isinstance(parse_result, tuple) and len(parse_result) == 3:
            (currency_code, account_number, statements) = parse_result
            for stmt_vals in statements:
                stmt_vals['currency_code'] = currency_code
                stmt_vals['account_number'] = account_number
        else:
            statements = parse_result
        # Check raw data:
        self._check_parsed_data(statements)
        # Import all statements:
        for stmt_vals in statements:
            (statement_id, new_notifications) = (
                self._import_statement(stmt_vals))
            if statement_id:
                statement_ids.append(statement_id)
            notifications.append(new_notifications)
        if len(statement_ids) == 0:
            raise Warning(_('You have already imported that file.'))
        return statement_ids, notifications

    @api.model
    def _import_statement(self, stmt_vals):
        """Import a single bank-statement.

        Return ids of created statements and notifications.
        """
        currency_code = stmt_vals.pop('currency_code')
        account_number = stmt_vals.pop('account_number')
        # Try to find the bank account and currency in odoo
        currency_id = self._find_currency_id(currency_code)
        bank_account_id = self._find_bank_account_id(account_number)
        if not bank_account_id and account_number:
            raise Warning(_('Can not find the account number %s.') %
                          account_number)
        # Find the bank journal
        journal_id = self._get_journal(currency_id, bank_account_id)
        # By now journal and account_number must be known
        if not journal_id:
            raise Warning(_('Can not determine journal for import.'))
        # Prepare statement data to be used for bank statements creation
        stmt_vals = self._complete_statement(
            stmt_vals, journal_id, account_number)
        # Create the bank stmt_vals
        return self._create_bank_statement(stmt_vals)

    @api.model
    def _parse_file(self, data_file):
        """ Each module adding a file support must extends this method. It
        processes the file if it can, returns super otherwise, resulting in a
        chain of responsability.
        This method parses the given file and returns the data required by
        the bank statement import process, as specified below.
        - bank statements data: list of dict containing (optional
                                items marked by o) :
            -o currency code: string (e.g: 'EUR')
                The ISO 4217 currency code, case insensitive
            -o account number: string (e.g: 'BE1234567890')
                The number of the bank account which the statement
                belongs to
            - 'name': string (e.g: '000000123')
            - 'date': date (e.g: 2013-06-26)
            -o 'balance_start': float (e.g: 8368.56)
            -o 'balance_end_real': float (e.g: 8888.88)
            - 'transactions': list of dict containing :
                - 'name': string
                    (e.g: 'KBC-INVESTERINGSKREDIET 787-5562831-01')
                - 'date': date
                - 'amount': float
                - 'unique_import_id': string
                -o 'account_number': string
                    Will be used to find/create the res.partner.bank
                    in odoo
                -o 'note': string
                -o 'partner_name': string
                -o 'ref': string
        """
        raise Warning(_(
            'Could not make sense of the given file.\n'
            'Did you install the module to support this type of file?'
        ))

    @api.model
    def _check_parsed_data(self, statements):
        """ Basic and structural verifications """
        if len(statements) == 0:
            raise Warning(_('This file doesn\'t contain any statement.'))
        for stmt_vals in statements:
            if 'transactions' in stmt_vals and stmt_vals['transactions']:
                return
        # If we get here, no transaction was found:
        raise Warning(_('This file doesn\'t contain any transaction.'))

    @api.model
    def _find_currency_id(self, currency_code):
        """ Get res.currency ID."""
        if currency_code:
            currency_ids = self.env['res.currency'].search(
                [('name', '=ilike', currency_code)])
            if currency_ids:
                return currency_ids[0].id
            else:
                raise Warning(_(
                    'Statement has invalid currency code %s') % currency_code)
        # if no currency_code is provided, we'll use the company currency
        return self.env.user.company_id.currency_id.id

    @api.model
    def _find_bank_account_id(self, account_number):
        """ Get res.partner.bank ID """
        bank_account_id = None
        if account_number and len(account_number) > 4:
            bank_account_ids = self.env['res.partner.bank'].search(
                [('acc_number', '=', account_number)], limit=1)
            if bank_account_ids:
                bank_account_id = bank_account_ids[0].id
        return bank_account_id

    @api.model
    def _get_journal(self, currency_id, bank_account_id):
        """ Find the journal """
        bank_model = self.env['res.partner.bank']
        # Find the journal from context, wizard or bank account
        journal_id = self.env.context.get('journal_id') or self.journal_id.id
        if bank_account_id:
            bank_account = bank_model.browse(bank_account_id)
            if journal_id:
                if (bank_account.journal_id.id and
                        bank_account.journal_id.id != journal_id):
                    raise Warning(
                        _('The account of this statement is linked to '
                          'another journal.'))
                if not bank_account.journal_id.id:
                    bank_model.write({'journal_id': journal_id})
            else:
                if bank_account.journal_id.id:
                    journal_id = bank_account.journal_id.id
        # If importing into an existing journal, its currency must be the same
        # as the bank statement. When journal has no currency, currency must
        # be equal to company currency.
        if journal_id and currency_id:
            journal_obj = self.env['account.journal'].browse(journal_id)
            if journal_obj.currency:
                journal_currency_id = journal_obj.currency.id
                if currency_id != journal_currency_id:
                    # ALso log message with id's for technical analysis:
                    _logger.warn(
                        _('Statement currency id is %d,'
                          ' but journal currency id = %d.'),
                        currency_id,
                        journal_currency_id
                    )
                    raise Warning(_(
                        'The currency of the bank statement is not '
                        'the same as the currency of the journal !'
                    ))
            else:
                company_currency_id = self.env.user.company_id.currency_id.id
                if currency_id != company_currency_id:
                    # ALso log message with id's for technical analysis:
                    _logger.warn(
                        _('Statement currency id is %d,'
                          ' but company currency id = %d.'),
                        currency_id,
                        company_currency_id
                    )
                    raise Warning(_(
                        'The currency of the bank statement is not '
                        'the same as the company currency !'
                    ))
        return journal_id

    @api.model
    @api.returns('res.partner.bank')
    def _create_bank_account(
            self, account_number, company_id=False, currency_id=False):
        """Automagically create bank account, when not yet existing."""
        try:
            bank_type = self.env.ref('base.bank_normal')
            bank_code = bank_type.code
        except ValueError:
            bank_code = 'bank'
        vals_acc = {
            'acc_number': account_number,
            'state': bank_code,
        }
        # Odoo users bank accounts (which we import statement from) have
        # company_id and journal_id set while 'counterpart' bank accounts
        # (from which statement transactions originate) don't.
        # Warning : if company_id is set, the method post_write of class
        # bank will create a journal
        if company_id:
            vals = self.env['res.partner.bank'].onchange_company_id(company_id)
            vals_acc.update(vals.get('value', {}))
            vals_acc['company_id'] = company_id

        # When the journal is created at same time of the bank account, we need
        # to specify the currency to use for the account.account and
        # account.journal
        return self.env['res.partner.bank'].with_context(
            default_currency_id=currency_id,
            default_currency=currency_id).create(vals_acc)

    @api.model
    def _complete_statement(self, stmt_vals, journal_id, account_number):
        """Complete statement from information passed."""
        stmt_vals['journal_id'] = journal_id
        for line_vals in stmt_vals['transactions']:
            unique_import_id = line_vals.get('unique_import_id', False)
            if unique_import_id:
                line_vals['unique_import_id'] = (
                    (account_number and account_number + '-' or '') +
                    unique_import_id
                )
            if not line_vals.get('bank_account_id'):
                # Find the partner and his bank account or create the bank
                # account. The partner selected during the reconciliation
                # process will be linked to the bank when the statement is
                # closed.
                partner_id = False
                bank_account_id = False
                account_number = line_vals.get('account_number')
                if account_number:
                    bank_model = self.env['res.partner.bank']
                    banks = bank_model.search(
                        [('acc_number', '=', account_number)], limit=1)
                    if banks:
                        bank_account_id = banks[0].id
                        partner_id = banks[0].partner_id.id
                    else:
                        bank_obj = self._create_bank_account(account_number)
                        bank_account_id = bank_obj and bank_obj.id or False
                line_vals['partner_id'] = partner_id
                line_vals['bank_account_id'] = bank_account_id
        return stmt_vals

    @api.model
    def _create_bank_statement(self, stmt_vals):
        """ Create bank statement from imported values, filtering out
        already imported transactions, and return data used by the
        reconciliation widget
        """
        bs_model = self.env['account.bank.statement']
        bsl_model = self.env['account.bank.statement.line']
        # Filter out already imported transactions and create statement
        ignored_line_ids = []
        filtered_st_lines = []
        for line_vals in stmt_vals['transactions']:
            unique_id = (
                'unique_import_id' in line_vals and
                line_vals['unique_import_id']
            )
            if not unique_id or not bool(bsl_model.sudo().search(
                    [('unique_import_id', '=', unique_id)], limit=1)):
                filtered_st_lines.append(line_vals)
            else:
                ignored_line_ids.append(unique_id)
        statement_id = False
        if len(filtered_st_lines) > 0:
            # Remove values that won't be used to create records
            stmt_vals.pop('transactions', None)
            for line_vals in filtered_st_lines:
                line_vals.pop('account_number', None)
            # Create the statement
            stmt_vals['line_ids'] = [
                [0, False, line] for line in filtered_st_lines]
            statement_id = bs_model.create(stmt_vals).id
        # Prepare import feedback
        notifications = []
        num_ignored = len(ignored_line_ids)
        if num_ignored > 0:
            notifications += [{
                'type': 'warning',
                'message':
                    _("%d transactions had already been imported and "
                      "were ignored.") % num_ignored
                    if num_ignored > 1
                    else _("1 transaction had already been imported and "
                           "was ignored."),
                'details': {
                    'name': _('Already imported items'),
                    'model': 'account.bank.statement.line',
                    'ids': bsl_model.search(
                        [('unique_import_id', 'in', ignored_line_ids)]).ids}
            }]
        return statement_id, notifications
